"""Gateway API + LLM proxy integration tests (API-1…11, PRX-1…5) and gateway self-security. Offline."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.llm.router import ChatResult
from intentseal_core.store import Store
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

    async def stream_chat(self, role: str, req: Any) -> "FakeStream":
        self.requests.append(req)
        tcs, self.tool_calls = self.tool_calls, []
        return FakeStream(self.content if not tcs else "Checking that for you.", tcs, getattr(self, "fail_mid_stream", False))

    async def aclose(self) -> None:
        return None


class FakeStream:
    """Upstream SSE chunks as providers send them: text in pieces, tool-call arguments split across chunks."""

    provider, model = "fake", "m"

    def __init__(self, content: str, tool_calls: list[dict[str, Any]], fail: bool = False) -> None:
        self.content, self.tool_calls, self.fail = content, tool_calls, fail
        self.handle = type("H", (), {"input_tokens": 5, "output_tokens": 7})()

    async def chunks(self):
        for word in self.content.split(" "):
            yield {"choices": [{"index": 0, "delta": {"content": word + " "}, "finish_reason": None}]}
        for i, call in enumerate(self.tool_calls):
            args = call["function"]["arguments"]
            half = len(args) // 2
            yield {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": i, "id": call["id"], "type": "function",
                   "function": {"name": call["function"]["name"], "arguments": args[:half]}}]}, "finish_reason": None}]}
            if self.fail:
                raise RuntimeError("connection reset")
            yield {"choices": [{"index": 0, "delta": {"tool_calls": [{"index": i, "function": {"arguments": args[half:]}}]},
                                "finish_reason": None}]}
        yield {"choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls" if self.tool_calls else "stop"}]}


def tc(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"call_{name}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", f"admin:{ADMIN}:admin,proj:{PROJECT}:project")
    monkeypatch.setenv("INTENTSEAL_PUBLIC_KEY", PUBLIC)
    monkeypatch.setenv("INTENTSEAL_CORS_ORIGINS", "https://console.example.test")
    monkeypatch.setenv("INTENTSEAL_CANARIES", "sk-canary-unit-test-0001")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "r.json").write_text(json.dumps({"suite": "headline", "protection": "on", "overall": {"asr": 0.0}}))
    scen = tmp_path / "scenarios"
    scen.mkdir()
    (scen / "s8.yaml").write_text("id: S8\ntitle: Benign article\nchannel: web\ncontent: Solar costs fell 12 percent this year.\n"
                                  "task: Summarise https://fixtures.test/incoming.html\n")
    monkeypatch.setenv("INTENTSEAL_SCENARIO_DIR", str(scen))
    return tmp_path


def make_client(env, router: FakeRouter | None = None, judge: float = 0.0):
    import importlib

    import intentseal_gateway.app as appmod
    import intentseal_gateway.demo as demomod
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
    monkeypatch.setenv("INTENTSEAL_PUBLIC_RATE_LIMIT_PER_MIN", "3")
    monkeypatch.setenv("INTENTSEAL_MAX_BODY_BYTES", "2000")
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
        r = c.post("/proxy/research-agent/v1/chat/completions",
                   json={"messages": [{"role": "user", "content": "hi"}], "stream": True}, headers=H(PROJECT))
        assert r.status_code == 200 and "data: [DONE]" in r.text

    class Down(FakeRouter):
        async def chat(self, role, req):
            from intentseal_core.llm.router import AllProvidersFailed
            raise AllProvidersFailed(role, [])

    with make_client(env, Down()) as c:
        r = c.post("/proxy/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]},
                   headers={**H(PROJECT), "X-Agent-Id": "research-agent"})
        assert r.status_code == 503


def test_demo_scenarios_and_run(env):
    router = FakeRouter(tool_calls=[tc("web_fetch", {"url": "https://fixtures.test/incoming.html"})], content="Costs fell 12%.")
    with make_client(env, router) as c:
        sc = c.get("/demo/scenarios", headers=H(PUBLIC)).json()
        assert sc[0]["id"] == "S8"
        out = c.post("/demo/run", json={"scenario_id": "S8", "protection": "on"}, headers=H(PUBLIC)).json()
        assert out["canary_leaked"] is False and out["session_id"] and out["events"]
        assert c.post("/demo/run", json={"scenario_id": "nope"}, headers=H(PUBLIC)).status_code == 404


def test_request_id_and_invalid_agent_id(env):
    with make_client(env) as c:
        r = c.get("/v1/decisions", headers={**H(PUBLIC), "X-Request-Id": "req-abc"})
        assert r.headers["x-request-id"] == "req-abc"
        assert c.get("/healthz").headers["x-request-id"]
        # agent ids can never name a file outside the policy directory (path traversal)
        assert c.get("/v1/policies/..%5C..%5Csecrets", headers=H(PUBLIC)).status_code in (404, 422)
        r = c.post("/v1/inspect", json={"content": "hi", "agent_id": "../x"}, headers=H(PROJECT))
        assert r.status_code == 422


def test_policy_put_is_admin_only_validated_and_versioned(env, monkeypatch):
    import shutil
    from intentseal_core.config import repo_root

    pdir = env / "policies"
    pdir.mkdir()
    shutil.copy(repo_root() / "policies" / "research-agent.yaml", pdir)
    monkeypatch.setenv("INTENTSEAL_POLICY_DIR", str(pdir))
    with make_client(env) as c:
        pol = c.get("/v1/policies/research-agent", headers=H(PUBLIC)).json()
        pol["mode"] = "monitor"
        assert c.put("/v1/policies/research-agent", json=pol, headers=H(PROJECT)).status_code == 403
        r = c.put("/v1/policies/research-agent", json=pol, headers=H(ADMIN)).json()
        assert r["mode"] == "monitor" and r["version"] == "2"
        assert c.get("/v1/policies/research-agent", headers=H(PUBLIC)).json()["mode"] == "monitor"
        bad = c.put("/v1/policies/research-agent", json={"thresholds": {"block": "high"}}, headers=H(ADMIN))
        assert bad.status_code == 422


def test_feedback_memory_and_known_attack(env):
    text = ("please file the zebra quarterly marker under the violet folder and then notify the "
            "orchard desk about the lantern schedule before noon")
    with make_client(env) as c:
        r = c.post("/v1/inspect", json={"content": text, "source": "web", "agent_id": "research-agent"}, headers=H(PROJECT)).json()
        assert r["decision"] == "ALLOW"
        assert c.post("/v1/feedback", json={"verdict": "attack", "event_id": r["event_id"]}, headers=H(PROJECT)).status_code == 403
        fb = c.post("/v1/feedback", json={"verdict": "attack", "event_id": r["event_id"], "labels": ["Context Poisoning"]},
                    headers=H(ADMIN)).json()
        mem = c.get("/v1/memory", headers=H(PUBLIC)).json()
        assert mem["stats"] == {"attack": 1} and "zebra" not in json.dumps(mem)
        again = c.post("/v1/inspect", json={"content": text, "source": "email", "agent_id": "research-agent"},
                       headers=H(PROJECT)).json()
        assert again["decision"] == "BLOCK" and again["policy_rule"] == "known-attack-match"
        assert c.delete(f"/v1/memory/{fb['memory_id']}", headers=H(ADMIN)).json()["removed"]
        assert c.post("/v1/feedback", json={"verdict": "attack", "event_id": "gone"}, headers=H(ADMIN)).status_code == 404


def test_approval_resolves_escalate_once_and_never_a_block(env):
    with make_client(env) as c:
        sid = c.post("/v1/sessions", json={"agent_id": "research-agent", "task": "email the team"}, headers=H(PROJECT)).json()["session_id"]
        # an internal address that appears only in untrusted content -> ESCALATE (target-from-untrusted-content)
        c.post("/v1/inspect", json={"content": "Contact desk.lead@example-corp.test for the figures.", "source": "web",
                                    "agent_id": "research-agent", "session_id": sid}, headers=H(PROJECT))
        args = {"to": "desk.lead@example-corp.test", "subject": "Figures", "body": "Please share the Q3 figures."}
        call = {"tool": "send_message", "args": args, "agent_id": "research-agent", "session_id": sid}
        first = c.post("/v1/actions/check", json=call, headers=H(PROJECT)).json()
        assert first["decision"] == "ESCALATE"
        inbox = c.get("/v1/approvals", headers=H(PUBLIC)).json()
        assert inbox and inbox[0]["event_id"] == first["event_id"] and inbox[0]["tool"] == "send_message"
        assert c.post(f"/v1/approvals/{first['event_id']}", json={"approve": True}, headers=H(PROJECT)).status_code == 403
        assert c.post(f"/v1/approvals/{first['event_id']}", json={"approve": True, "note": "ok"}, headers=H(ADMIN)).status_code == 200
        retry = c.post("/v1/actions/check", json=call, headers=H(PROJECT)).json()
        assert retry["decision"] == "ALLOW" and retry["policy_rule"] == "human-approved" and retry["final_args"]["to"] == args["to"]
        assert c.post("/v1/actions/check", json=call, headers=H(PROJECT)).json()["decision"] == "ESCALATE"   # one-shot
        assert c.post(f"/v1/approvals/{first['event_id']}", json={"approve": True}, headers=H(ADMIN)).status_code == 404
        blocked = c.post("/v1/actions/check", json={**call, "args": {**args, "to": "x@elsewhere.test"}}, headers=H(PROJECT)).json()
        assert blocked["decision"] == "BLOCK" and not c.get("/v1/approvals?status=pending", headers=H(PUBLIC)).json()[0]["tool"] != "send_message"


def test_metrics_and_cost_overhead(env):
    with make_client(env) as c:
        c.post("/v1/inspect", json={"content": "Revenue grew 8%.", "source": "web", "agent_id": "research-agent"}, headers=H(PROJECT))
        m = c.get("/v1/metrics", headers=H(PUBLIC)).json()
        assert m["inspections"]["n"] == 1 and m["by_decision"] == {"ALLOW": 1}
        assert m["latency_ms"]["fast_path"]["p50"] is not None and m["memory"] == {}
        costs = c.get("/v1/costs", headers=H(PUBLIC)).json()
        assert {"token_ratio", "cost_ratio", "unpriced_models"} <= set(costs["overhead"])
        assert c.get("/v1/costs/research-agent", headers=H(PUBLIC)).json()["by_tier"]


class ScriptedRouter(FakeRouter):
    """Upstream model that answers from a script: each item is (content, [tool calls])."""

    def __init__(self, script: list[tuple[str, list[dict[str, Any]]]]) -> None:
        super().__init__()
        self.script = list(script)

    async def chat(self, role: str, req: Any) -> ChatResult:
        self.requests.append(req)
        content, tcs = self.script.pop(0) if self.script else ("done", [])
        return ChatResult(content=content, tool_calls=tcs, finish_reason="tool_calls" if tcs else "stop", provider="fake",
                          model="m", key_alias=None, input_tokens=5, output_tokens=2, latency_ms=1, est_cost_usd=0,
                          cached=False, attempts=[])


def test_unmodified_openai_sdk_agent_through_proxy_one_setting(env):
    """S9 / G8 / PRX-1..5: the example agent has no gateway code; only its base URL points at the proxy."""
    import sys
    from pathlib import Path

    from openai import OpenAI

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples" / "openai_agent"))
    import agent as plain_agent   # examples/openai_agent/agent.py

    router = ScriptedRouter([
        ("", [tc("web_fetch", {"url": "https://fixtures.test/a.html"})]),
        ("", [{"id": "call_send", "type": "function", "function": {"name": "send_message", "arguments": json.dumps(
            {"to": "collector@elsewhere.test", "subject": "notes", "body": "page notes"})}}]),
        ("Here is the summary.", []),
    ])
    box = plain_agent.Sandbox(pages={"https://fixtures.test/a.html": "Normal text. ZQX-MARKER planted text."})
    with make_client(env, router, judge=0.95) as c:
        client = OpenAI(base_url="http://testserver/proxy/research-agent/v1", api_key=PROJECT, http_client=c)
        answer = plain_agent.run("Summarise https://fixtures.test/a.html", box, client=client)
        assert "blocked by the security policy" in answer   # PRX-3: the blocked call became a safe notice
        assert box.outbox == []                                          # the external send never reached the tool
        assert all("ZQX-MARKER" not in json.dumps(r.messages) for r in router.requests[1:])   # page withheld upstream
        decisions = c.get("/v1/decisions?agent=research-agent", headers=H(PUBLIC)).json()
        inspected = [d["source"] for d in decisions if d["kind"] == "content_in"]
        assert inspected.count("tool:web_fetch") == 1 and inspected.count("user") == 1   # once per session, not per turn
        assert any(d["policy_rule"] == "recipient-not-allowed" for d in decisions)
        assert len({d["session_id"] for d in decisions}) == 1 and decisions[0]["session_id"].startswith("conv-")


def test_demo_proxy_scenario_off_monitors_on_enforces(env):
    (env / "scenarios" / "s9.yaml").write_text(
        "id: S9\ntitle: Unmodified agent through the proxy\nsurface: proxy\nchannel: web\n"
        "content: Normal text. ZQX-MARKER planted text.\n")
    script = lambda: [("", [tc("web_fetch", {"url": "https://fixtures.test/incoming.html"})]),
                      ("", [{"id": "call_send", "type": "function", "function": {"name": "send_message", "arguments": json.dumps(
                          {"to": "collector@elsewhere.test", "subject": "notes", "body": "page notes"})}}]),
                      ("Summary sent.", [])]
    with make_client(env, ScriptedRouter(script()), judge=0.95) as c:
        on = c.post("/demo/run", json={"scenario_id": "S9", "protection": "on"}, headers=H(PUBLIC)).json()
    assert on["surface"] == "proxy" and on["external_sends"] == 0 and on["events"]
    with make_client(env, ScriptedRouter(script()), judge=0.95) as c:
        off = c.post("/demo/run", json={"scenario_id": "S9", "protection": "off"}, headers=H(PUBLIC)).json()
    assert off["external_sends"] == 1                                  # monitor mode: logged, not enforced
    assert any(e["decision"] == "BLOCK" and e["enforced"] == "ALLOW" for e in off["events"])


def test_empty_env_values_mean_defaults(env, monkeypatch):
    # Copying .env.example leaves optional settings empty; the gateway must start with defaults, not crash on int("").
    for k in ("INTENTSEAL_RATE_LIMIT_PER_MIN", "INTENTSEAL_PUBLIC_RATE_LIMIT_PER_MIN", "INTENTSEAL_MAX_BODY_BYTES", "INTENTSEAL_EXTRACT_TIMEOUT_S"):
        monkeypatch.setenv(k, "")
    with make_client(env) as c:
        assert c.get("/healthz").status_code == 200
        assert c.get("/v1/decisions", headers=H(PUBLIC)).status_code == 200


def test_decisions_feed_pages_with_before_cursor(env):
    with make_client(env) as c:
        for i in range(5):
            c.post("/v1/inspect", json={"content": f"Revenue grew {i}%.", "source": "web", "agent_id": "research-agent"}, headers=H(PROJECT))
        first = c.get("/v1/decisions?limit=2", headers=H(PUBLIC)).json()
        second = c.get(f"/v1/decisions?limit=2&before={first[-1]['created_at']}", headers=H(PUBLIC)).json()
        assert len(first) == 2 and len(second) == 2
        assert {r["event_id"] for r in first}.isdisjoint(r["event_id"] for r in second)
        assert all(r["created_at"] < first[-1]["created_at"] for r in second)
        assert c.get("/v1/decisions?limit=0", headers=H(PUBLIC)).status_code == 422


def test_whoami_reports_scope_for_console_sign_in(env):
    with make_client(env) as c:
        assert c.get("/v1/whoami", headers=H(ADMIN)).json() == {"name": "admin", "scope": "admin", "org": "default", "agents": None}
        assert c.get("/v1/whoami", headers=H(PUBLIC)).json()["scope"] == "public"
        assert c.get("/v1/whoami", headers=H("nope")).status_code == 401


def test_policy_round_trip_keeps_redacted_canaries(env, monkeypatch):
    import yaml as _yaml

    pdir = env / "policies"
    pdir.mkdir()
    (pdir / "demo-agent.yaml").write_text(_yaml.safe_dump({"agent": "demo-agent", "mode": "enforce",
                                                             "sensitive_data": {"canaries": ["from_env", "sk-literal-canary-0001"]}}))
    monkeypatch.setenv("INTENTSEAL_POLICY_DIR", str(pdir))
    with make_client(env) as c:
        got = c.get("/v1/policies/demo-agent", headers=H(PUBLIC)).json()
        assert got["sensitive_data"]["canaries"] == ["from_env", "[REDACTED]"]
        got["mode"] = "monitor"
        assert c.put("/v1/policies/demo-agent", json=got, headers=H(ADMIN)).status_code == 200
    saved = _yaml.safe_load((pdir / "demo-agent.yaml").read_text())
    assert saved["mode"] == "monitor" and saved["sensitive_data"]["canaries"] == ["from_env", "sk-literal-canary-0001"]


def test_unknown_agent_is_refused_not_run_unprotected(env):
    """F4: an agent with no policy file would run the default monitor policy (nothing enforced): 404 instead."""
    with make_client(env, FakeRouter(content="hello")) as c:
        body = {"messages": [{"role": "user", "content": "hi"}]}
        assert c.post("/proxy/v1/chat/completions", json=body, headers=H(PROJECT)).status_code == 404   # default-agent
        assert c.post("/proxy/reserch-agent/v1/chat/completions", json=body, headers=H(PROJECT)).status_code == 404
        assert c.post("/v1/inspect", json={"content": "hi", "agent_id": "no-such-agent"}, headers=H(PROJECT)).status_code == 404
        assert c.post("/v1/actions/check", json={"tool": "read_file", "args": {}, "agent_id": "no-such-agent"},
                      headers=H(PROJECT)).status_code == 404
        assert c.get("/v1/policies/no-such-agent", headers=H(PUBLIC)).status_code == 404
        assert c.post("/proxy/research-agent/v1/chat/completions", json=["not", "a", "request"],
                      headers=H(PROJECT)).status_code == 422


def test_chunked_body_over_limit_is_rejected_while_streaming(env, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_MAX_BODY_BYTES", "2000")
    sent = []

    def body():   # no Content-Length: the limit must be enforced as chunks arrive
        for _ in range(100):
            sent.append(1)
            yield b"x" * 1000

    with make_client(env) as c:
        r = c.post("/v1/inspect", content=body(), headers={**H(PROJECT), "Content-Type": "application/json"})
        assert r.status_code == 413


def _events(text: str) -> list[Any]:
    out = []
    for line in text.splitlines():
        if line.startswith("data: ") and line != "data: [DONE]":
            out.append(json.loads(line[6:]))
    return out


def test_proxy_streams_text_and_releases_only_checked_tool_calls(env):
    """PRX-6: text streams through; tool calls are buffered, assembled, checked, then released or replaced."""
    router = FakeRouter(tool_calls=[tc("send_message", {"to": "x@elsewhere.test", "subject": "s", "body": "b"}),
                                    tc("query_db", {"customer_id": "C-2001"})])
    with make_client(env, router) as c:
        sid = c.post("/v1/sessions", json={"agent_id": "research-agent", "task": "look up C-1042",
                                           "trusted": {"customer_id": "C-1042"}}, headers=H(PROJECT)).json()["session_id"]
        body = {"messages": [{"role": "user", "content": "Look up customer C-1042"}], "stream": True,
                "stream_options": {"include_usage": True}}
        r = c.post("/proxy/research-agent/v1/chat/completions", json=body, headers={**H(PROJECT), "X-Session-Id": sid})
        assert r.status_code == 200 and r.text.rstrip().endswith("data: [DONE]")
        events = _events(r.text)
        deltas = [e["choices"][0]["delta"] for e in events if e.get("choices")]
        text_chunks = [d["content"] for d in deltas if d.get("content")]
        assert len(text_chunks) >= 3 and text_chunks[0].startswith("Checking")      # streamed, not one block
        released = [tc for d in deltas for tc in d.get("tool_calls", [])]
        assert [t["function"]["name"] for t in released] == ["query_db"]           # send_message never released
        assert json.loads(released[0]["function"]["arguments"]) == {"customer_id": "C-1042"}   # pinned, whole
        assert "elsewhere.test" not in r.text and "blocked" in "".join(text_chunks)
        final = [e for e in events if e.get("choices") and e["choices"][0]["finish_reason"]][-1]
        assert final["choices"][0]["finish_reason"] == "tool_calls" and final["x_security"]["blocked_tool_calls"] == 1
        assert events[-1]["usage"]["total_tokens"] == 12


def test_proxy_stream_failure_never_releases_a_partial_tool_call(env):
    router = FakeRouter(tool_calls=[tc("query_db", {"customer_id": "C-1042"})])
    router.fail_mid_stream = True
    with make_client(env, router) as c:
        r = c.post("/proxy/research-agent/v1/chat/completions",
                   json={"messages": [{"role": "user", "content": "Look up C-1042"}], "stream": True}, headers=H(PROJECT))
        events = _events(r.text)
        assert any("error" in e for e in events)
        assert not any(d.get("tool_calls") for e in events for d in [e.get("choices", [{}])[0].get("delta", {})] if e.get("choices"))


def test_openai_sdk_streaming_client_gets_checked_tool_call(env):
    from openai import OpenAI

    router = FakeRouter(tool_calls=[tc("query_db", {"customer_id": "C-1042"})])
    with make_client(env, router) as c:
        client = OpenAI(base_url="http://testserver/proxy/research-agent/v1", api_key=PROJECT, http_client=c)
        stream = client.chat.completions.create(model="any", messages=[{"role": "user", "content": "Look up C-1042"}],
                                                stream=True)
        names, args, text = [], "", ""
        for chunk in stream:
            if not chunk.choices:
                continue
            d = chunk.choices[0].delta
            text += d.content or ""
            for call in d.tool_calls or []:
                names.append(call.function.name)
                args += call.function.arguments or ""
        assert names == ["query_db"] and json.loads(args) == {"customer_id": "C-1042"} and text.startswith("Checking")


def test_readiness_reports_checks(env):
    with make_client(env) as c:
        r = c.get("/readyz")
        assert r.status_code == 200 and r.json()["ready"] and r.json()["checks"]["database"]
        assert r.json()["judge"].startswith("unavailable")          # the fake router has no providers configured


def test_demo_runs_have_an_hourly_cap(env, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_DEMO_RUNS_PER_HOUR", "1")
    router = FakeRouter(content="Costs fell 12%.")
    with make_client(env, router) as c:
        assert c.post("/demo/run", json={"scenario_id": "S8", "protection": "off"}, headers=H(PUBLIC)).status_code == 200
        r = c.post("/demo/run", json={"scenario_id": "S8", "protection": "off"}, headers=H(PUBLIC))
        assert r.status_code == 429 and int(r.headers["retry-after"]) > 0


def test_gateway_entry_point_seeds_a_writable_policy_dir(monkeypatch, tmp_path):
    from intentseal_gateway.__main__ import seed_policies

    target = tmp_path / "data" / "policies"
    monkeypatch.setenv("INTENTSEAL_POLICY_DIR", str(target))
    seed_policies()
    assert (target / "research-agent.yaml").exists()
    (target / "research-agent.yaml").write_text("agent: research-agent\nmode: enforce\n", encoding="utf-8")
    seed_policies()                                                   # never overwrites edited policies
    assert "mode: enforce" in (target / "research-agent.yaml").read_text(encoding="utf-8")
