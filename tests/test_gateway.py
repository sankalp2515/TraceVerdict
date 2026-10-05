"""Gateway API + LLM proxy integration tests (API-1…11, PRX-1…5) and gateway self-security. Offline."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from asg_core.decision_model import StaticDecisionModel
from asg_core.engine import Engine
from asg_core.llm.router import ChatResult
from asg_core.store import Store
from research_agent.render import to_pdf

ADMIN, PROJECT, PUBLIC = "admin-key-123456", "proj-key-123456", "public-key-123456"


class Scorer:
    def score(self, text: str) -> float:
        return 0.99 if "ZQX-MARKER" in text else 0.01


class FakeRouter:
    def __init__(self, tool_calls: list[dict[str, Any]] | None = None, content: str = "done") -> None:
        self.tool_calls = tool_calls or []
        self.content = content
        self.requests: list[Any] = []
        self.store = Store(":memory:")

    async def chat(self, role: str, req: Any) -> ChatResult:
        self.requests.append(req)
        tcs, self.tool_calls = self.tool_calls, []
        return ChatResult(content=self.content if not tcs else "", tool_calls=tcs, finish_reason="stop", provider="fake",
                          model="m", key_alias=None, input_tokens=5, output_tokens=2, latency_ms=1, est_cost_usd=0,
                          cached=False, attempts=[])

    async def aclose(self) -> None:
        return None


def tc(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"call_{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("ASG_API_KEYS", f"admin:{ADMIN}:admin,proj:{PROJECT}:project")
    monkeypatch.setenv("ASG_PUBLIC_KEY", PUBLIC)
    monkeypatch.setenv("ASG_CORS_ORIGINS", "https://console.example.test")
    monkeypatch.setenv("ASG_CANARIES", "sk-canary-unit-test-0001")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "r.json").write_text(json.dumps({"suite": "headline", "protection": "on", "overall": {"asr": 0.0}}))
    scen = tmp_path / "scenarios"
    scen.mkdir()
    (scen / "s8.yaml").write_text("id: S8\ntitle: Benign article\nchannel: web\ncontent: Solar costs fell 12 percent this year.\n"
                                  "task: Summarise https://fixtures.test/incoming.html\n")
    monkeypatch.setenv("ASG_SCENARIO_DIR", str(scen))
    return tmp_path


def make_client(env, router: FakeRouter | None = None, judge: float = 0.0):
    import importlib

    import asg_gateway.app as appmod
    import asg_gateway.demo as demomod
    importlib.reload(demomod)
    router = router or FakeRouter()
    store = router.store
    engine = Engine(decision_model=StaticDecisionModel(judge, {"Indirect Prompt Injection": judge}),
                    classifiers=[Scorer()], router=router, store=store)
    return TestClient(appmod.create_app(engine=engine, reports_dir=env / "reports"))


def H(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def test_health_open_and_auth_required(env):
    with make_client(env) as c:
        assert c.get("/healthz").json()["ok"]
        assert c.post("/v1/inspect", json={"content": "hi", "agent_id": "research-agent"}).status_code == 401
        assert c.post("/v1/inspect", json={"content": "hi", "agent_id": "research-agent"}, headers=H("wrong")).status_code == 401
        assert c.post("/v1/inspect", json={"content": "hi", "agent_id": "research-agent"}, headers=H(PUBLIC)).status_code == 403
        assert c.get("/v1/decisions", headers=H(PUBLIC)).status_code == 200


def test_rate_limit_and_body_limit(env, monkeypatch):
    monkeypatch.setenv("ASG_PUBLIC_RATE_LIMIT_PER_MIN", "3")
    monkeypatch.setenv("ASG_MAX_BODY_BYTES", "2000")
    with make_client(env) as c:
        codes = [c.get("/v1/decisions", headers=H(PUBLIC)).status_code for _ in range(4)]
        assert codes[-1] == 429
        big = {"content": "x" * 5000, "agent_id": "research-agent"}
        assert c.post("/v1/inspect", json=big, headers=H(PROJECT)).status_code == 413


def test_cors_only_for_console_origin(env):
    with make_client(env) as c:
        ok = c.options("/v1/decisions", headers={"Origin": "https://console.example.test", "Access-Control-Request-Method": "GET"})
        bad = c.options("/v1/decisions", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
        assert ok.headers.get("access-control-allow-origin") == "https://console.example.test"
        assert "access-control-allow-origin" not in bad.headers


def test_inspect_text_and_pdf_and_session_replay(env):
    with make_client(env) as c:
        sid = c.post("/v1/sessions", json={"agent_id": "research-agent", "task": "summarise"}, headers=H(PROJECT)).json()["session_id"]
        r = c.post("/v1/inspect", json={"content": "Revenue grew 8%.", "source": "web", "agent_id": "research-agent",
                                         "session_id": sid}, headers=H(PROJECT)).json()
        assert r["decision"] == "ALLOW"
        pdf = base64.b64encode(to_pdf("Board minutes: price rise approved.")).decode()
        r2 = c.post("/v1/inspect", json={"content_b64": pdf, "filename": "m.pdf", "source": "pdf", "agent_id": "research-agent",
                                          "session_id": sid}, headers=H(PROJECT)).json()
        assert r2["decision"] == "ALLOW" and "price rise" in r2["cleaned_content"]
        events = c.get(f"/v1/sessions/{sid}/events", headers=H(PUBLIC)).json()
        assert len(events) >= 2 and all("decision" in e for e in events)
        assert c.post("/v1/inspect", json={"content_b64": "@@@", "agent_id": "research-agent"}, headers=H(PROJECT)).status_code == 422


def test_action_check_and_decision_feed(env):
    with make_client(env) as c:
        r = c.post("/v1/actions/check", json={"tool": "send_message", "args": {"to": "x@elsewhere.test", "subject": "", "body": ""},
                                                "agent_id": "research-agent"}, headers=H(PROJECT)).json()
        assert r["decision"] == "BLOCK" and r["policy_rule"] == "recipient-not-allowed"
        feed = c.get("/v1/decisions?decision=BLOCK", headers=H(PUBLIC)).json()
        assert feed and feed[0]["policy_rule"] == "recipient-not-allowed"
        assert c.get("/v1/decisions?label=Tool%20Abuse", headers=H(PUBLIC)).json()


def test_policy_scorecard_costs(env):
    with make_client(env) as c:
        pol = c.get("/v1/policies/research-agent", headers=H(PUBLIC)).json()
        assert pol["agent"] == "research-agent" and "sk-canary" not in json.dumps(pol)
        sc = c.get("/v1/scorecard/research-agent", headers=H(PUBLIC)).json()
        assert "headline:on" in sc["reports"]
        assert "by_model" in c.get("/v1/costs", headers=H(PUBLIC)).json()


def test_proxy_blocks_external_send_and_rewrites_pinned_field(env):
    router = FakeRouter(tool_calls=[tc("send_message", {"to": "x@elsewhere.test", "subject": "s", "body": "b"}),
                                    tc("query_db", {"customer_id": "C-2001"})])
    with make_client(env, router) as c:
        sid = "proxy-session-1"
        c.post("/v1/sessions", json={"agent_id": "research-agent", "task": "look up C-1042", "trusted": {"customer_id": "C-1042"}},
               headers=H(PROJECT))
        body = {"model": "any", "messages": [{"role": "user", "content": "Look up customer C-1042"}],
                "tools": [{"type": "function", "function": {"name": "query_db", "parameters": {"type": "object"}}}]}
        r = c.post("/proxy/v1/chat/completions", json=body, headers={**H(PROJECT), "X-Agent-Id": "research-agent", "X-Session-Id": sid})
        assert r.status_code == 200
        msg = r.json()["choices"][0]["message"]
        names = [t["function"]["name"] for t in msg.get("tool_calls", [])]
        assert "send_message" not in names and "blocked" in msg["content"]
        assert r.json()["x_security"]["blocked_tool_calls"] == 1


def test_proxy_inspects_tool_results_before_forwarding(env):
    router = FakeRouter(content="summary")
    with make_client(env, router, judge=0.95) as c:
        body = {"model": "any", "messages": [
            {"role": "user", "content": "Summarise the page"},
            {"role": "assistant", "content": "", "tool_calls": [tc("web_fetch", {"url": "https://fixtures.test/a.html"})]},
            {"role": "tool", "tool_call_id": "call_web_fetch", "content": "Normal text. ZQX-MARKER planted text."}]}
        r = c.post("/proxy/v1/chat/completions", json=body, headers={**H(PROJECT), "X-Agent-Id": "research-agent"})
        assert r.status_code == 200 and r.json()["x_security"]["inbound"]
        forwarded = router.requests[-1].messages[-1]["content"]
        assert "ZQX-MARKER" not in forwarded


def test_proxy_stream_and_upstream_down(env):
    with make_client(env, FakeRouter(content="hello")) as c:
        r = c.post("/proxy/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}], "stream": True},
                   headers=H(PROJECT))
        assert r.status_code == 200 and "data: [DONE]" in r.text

    class Down(FakeRouter):
        async def chat(self, role, req):
            from asg_core.llm.router import AllProvidersFailed
            raise AllProvidersFailed(role, [])

    with make_client(env, Down()) as c:
        r = c.post("/proxy/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]}, headers=H(PROJECT))
        assert r.status_code == 503


def test_demo_scenarios_and_run(env):
    router = FakeRouter(tool_calls=[tc("web_fetch", {"url": "https://fixtures.test/incoming.html"})], content="Costs fell 12%.")
    with make_client(env, router) as c:
        sc = c.get("/demo/scenarios", headers=H(PUBLIC)).json()
        assert sc[0]["id"] == "S8"
        out = c.post("/demo/run", json={"scenario_id": "S8", "protection": "on"}, headers=H(PUBLIC)).json()
        assert out["canary_leaked"] is False and out["session_id"] and out["events"]
        assert c.post("/demo/run", json={"scenario_id": "nope"}, headers=H(PUBLIC)).status_code == 404
