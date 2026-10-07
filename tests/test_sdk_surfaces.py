"""SDK-6 remote mode, SDK-7 LangChain/LangGraph helper, G8 adoption size, CORE-1 no-bypass per surface.
Offline: static judge, stub classifier, scripted models."""

from __future__ import annotations

import difflib
import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.policy import load_policy
from intentseal_core.store import Store
from intentseal_core.types import Decision
from intentseal import Guard

ROOT = Path(__file__).resolve().parents[1]
KEY = "proj-key-123456"
MARK = "ZQX-MARKER"


class Scorer:
    def score(self, text: str) -> float:
        return 0.99 if MARK in text else 0.01


class Judge(StaticDecisionModel):
    async def assess(self, content, source, task=""):
        self.calls += 1
        return type(self.result)(0.95 if MARK in content else 0.0, {"Indirect Prompt Injection": 0.9} if MARK in content else {})


def make_engine() -> Engine:
    policy = load_policy("research-agent")
    policy.sensitive_data.canaries = []
    return Engine(policy_loader=lambda _: policy, decision_model=Judge(), classifiers=[Scorer()], store=Store(":memory:"))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def gateway(monkeypatch):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", f"proj:{KEY}:project")
    import intentseal_gateway.app as appmod
    with TestClient(appmod.create_app(engine=make_engine())) as c:
        yield c


CASES = [("Revenue grew 8% this quarter.", "web"), (f"Normal text. {MARK} planted text.", "web"),
         (f"Status update {MARK}", "email"), ("Please summarise the attached notes.", "user")]


async def test_remote_mode_gives_the_same_decisions_as_embedded(gateway):
    embedded = Guard("research-agent", engine=make_engine(), policy=load_policy("research-agent"), warm_up=False)
    remote = Guard("research-agent", api_key=KEY, http_client=gateway)
    for g in (embedded, remote):
        g.start_session(task="summarise")
    for content, source in CASES:
        a, b = await embedded.ainspect_result(content, source), await remote.ainspect_result(content, source)
        assert (a.decision, a.policy_rule, a.labels) == (b.decision, b.policy_rule, b.labels)
    call = ("send_message", {"to": "x@elsewhere.test", "subject": "s", "body": "b"})
    assert (await embedded.acheck(*call)).policy_rule == (await remote.acheck(*call)).policy_rule == "recipient-not-allowed"


async def test_remote_mode_fails_closed_when_the_gateway_is_down(gateway):
    remote = Guard("research-agent", api_key=KEY, http_client=gateway)
    remote.engine.headers = {"Authorization": "Bearer wrong"}          # every call now fails (401)
    assert "withheld" in await remote.ainspect("Revenue grew 8%.", "web")
    assert (await remote.acheck("send_message", {"to": "a@example-corp.test"})).enforced == Decision.BLOCK   # failure: closed
    assert (await remote.acheck("read_file", {"path": "a.txt"})).enforced == Decision.ALLOW              # failure: open


class ScriptedChat:
    """Minimal LangChain chat model for create_react_agent: replies from a script of tool calls."""

    def __new__(cls, script):
        from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
        from langchain_core.messages import AIMessage

        class _Model(FakeMessagesListChatModel):
            def bind_tools(self, tools, **kwargs):
                return self

        msgs = [AIMessage(content=c, tool_calls=[{"name": n, "args": a, "id": f"call_{i}"} for i, (n, a) in enumerate(t)])
                for c, t in script]
        return _Model(responses=msgs)


def test_langgraph_agent_protected_in_under_ten_lines():
    plain = (ROOT / "examples/langgraph_agent/agent.py").read_text(encoding="utf-8").splitlines()
    guarded = (ROOT / "examples/langgraph_agent/agent_protected.py").read_text(encoding="utf-8").splitlines()
    changed = [l for l in difflib.unified_diff(plain, guarded, lineterm="", n=0)
               if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
    assert len([l for l in changed if l.startswith("+")]) <= 10, changed   # G8: SDK adoption <= 10 lines


def test_langgraph_tools_checked_and_outputs_inspected():
    mod = load(ROOT / "examples/langgraph_agent/agent_protected.py", "lg_protected")
    mod.PAGES["https://fixtures.test/a.html"] = f"Normal text. {MARK} planted text."
    mod.OUTBOX.clear()
    model = ScriptedChat([("", [("web_fetch", {"url": "https://fixtures.test/a.html"})]),
                          ("", [("send_message", {"to": "collector@elsewhere.test", "subject": "s", "body": "b"})]),
                          ("Done.", [])])
    guard = Guard("research-agent", engine=make_engine(), policy=load_policy("research-agent"), warm_up=False)
    assert mod.run("Summarise https://fixtures.test/a.html", model=model, guard=guard) == "Done."
    assert mod.OUTBOX == []
    rules = [d["policy_rule"] for d in guard.engine.logger.decisions()]
    assert "recipient-not-allowed" in rules and "content-risk-block" in rules


def test_every_surface_goes_through_engine_inspect(gateway, monkeypatch):
    """CORE-1: SDK, Gateway API, LLM proxy and the LangChain helper all reach Engine.inspect (no bypass)."""
    seen: list[str] = []
    real = Engine.inspect

    async def spy(self, content, source, *a, **k):
        seen.append(source)
        return await real(self, content, source, *a, **k)

    monkeypatch.setattr(Engine, "inspect", spy)
    g = Guard("research-agent", engine=make_engine(), policy=load_policy("research-agent"), warm_up=False)
    g.inspect("hello there", "web")
    assert seen[-1] == "web"
    gateway.post("/v1/inspect", json={"content": "hi", "source": "pdf", "agent_id": "research-agent"},
                 headers={"Authorization": f"Bearer {KEY}"})
    assert seen[-1] == "pdf"
    class Upstream:   # proxy upstream stub: inbound inspection is what this test proves
        async def chat(self, role, req):
            from intentseal_core.llm.router import ChatResult
            return ChatResult(content="ok", tool_calls=[], finish_reason="stop", provider="fake", model="m", key_alias=None,
                              input_tokens=1, output_tokens=1, latency_ms=1, est_cost_usd=0, cached=False, attempts=[])

    gateway.app.state.engine.router = Upstream()
    gateway.post("/proxy/research-agent/v1/chat/completions", json={"messages": [
        {"role": "user", "content": "hi"}, {"role": "tool", "tool_call_id": "x", "content": "tool output text"}]},
        headers={"Authorization": f"Bearer {KEY}"})
    assert "user" in seen and "tool:tool" in seen
    from langchain_core.tools import tool

    @tool
    def web_fetch(url: str) -> str:
        """Fetch a page."""
        return "page text for " + url

    g.protect_tools([web_fetch])[0].invoke({"url": "https://fixtures.test/a.html"})
    assert seen[-1] == "tool:web_fetch"
    blocked = g.protect_tools([web_fetch])[0].invoke({"url": "https://elsewhere.test/a"})
    assert "blocked" in blocked and seen[-1] == "tool:web_fetch"   # unapproved domain: never runs, nothing to inspect
