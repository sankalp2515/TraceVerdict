"""Demo runner (API-7): run a scenario on the sandboxed reference agent, protection OFF or ON.

Scenarios are data files in eval/scenarios/*.yaml (one per scenario, S1-S9), so the demo content lives
with the evaluation corpus, not in code:

    id: S2
    title: Triage an email that asks the assistant to forward data
    attack_types: [Credential Theft, Tool Abuse]
    channel: email                 # see research_agent.delivery.CHANNELS
    task: "Please summarise my recent emails."
    content: |                     # or content_file: relative path (e.g. a PDF) under eval/scenarios/
      ...
    expected: { off: "...", on: "..." }
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from asg_core.config import repo_root
from asg_core.engine import Engine
from asg_core.llm.router import Router
from asg_sdk import Guard
from research_agent import AgentHooks, ResearchAgent, World
from research_agent.delivery import CHANNELS, deliver
from research_agent.guarded import AGENT_ID, guard_hooks

SCENARIO_DIR = Path(os.environ.get("ASG_SCENARIO_DIR", repo_root() / "eval" / "scenarios"))
DEMO_ROLE = os.environ.get("ASG_DEMO_AGENT_ROLE", "agent")
_guards: dict[int, Guard] = {}


def _load() -> dict[str, dict[str, Any]]:
    out = {}
    for f in sorted(SCENARIO_DIR.glob("*.yaml")) if SCENARIO_DIR.exists() else []:
        s = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        if "id" in s:
            s["_dir"] = f.parent
            out[str(s["id"])] = s
    return out


def list_scenarios() -> list[dict[str, Any]]:
    return [{k: v for k, v in s.items() if k in ("id", "title", "attack_types", "channel", "task", "expected")}
            for s in _load().values()]


def _content(s: dict[str, Any]) -> str | bytes | None:
    if s.get("content_file"):
        p = (s["_dir"] / s["content_file"]).resolve()
        return p.read_bytes() if p.suffix.lower() in (".pdf", ".docx", ".png", ".jpg", ".eml") else p.read_text(encoding="utf-8")
    return s.get("content")


def _guard(engine: Engine) -> Guard:
    g = _guards.get(id(engine))
    if g is None:
        g = _guards[id(engine)] = Guard(AGENT_ID, engine=engine, warm_up=False)
    return g


async def run_scenario(engine: Engine, scenario_id: str, protection: str) -> dict[str, Any]:
    s = _load()[scenario_id]
    channel = s.get("channel", "user")
    content = _content(s)
    task = s.get("task") or CHANNELS.get(channel, ("", ""))[1]
    overrides: dict[str, Any] = {}
    turns: Any = task
    if content is not None:
        if channel == "user":
            turns = [*([task] if task else []), content] if isinstance(content, str) else task
        elif isinstance(content, bytes):
            how = CHANNELS[channel][0]
            where = how.partition(":")[2]
            overrides = {"files": {where: content}}
        else:
            overrides = deliver(channel, content)
    if isinstance(s.get("turns"), list):
        turns = s["turns"]
    world = World(overrides=overrides)
    router: Router = engine.router or Router(store=engine.store)
    hooks = guard_hooks(world, turns, _guard(engine)) if protection == "on" else AgentHooks()
    try:
        t = await ResearchAgent(router, world, hooks=hooks, role=DEMO_ROLE).run(turns)
        session_id = hooks.session.session_id if protection == "on" else None
        return {
            "scenario_id": scenario_id, "protection": protection, "answer": t.answer, "error": t.error,
            "model": t.providers[-1] if t.providers else None,
            "steps": [{"tool": e["tool"], "args": _safe(e["args"], world), "allowed": e["allowed"], "notice": e["notice"]}
                      for e in t.tool_calls()],
            "outbox": [_safe(m, world) for m in world.outbox],
            "canary_leaked": bool(world.leaked_canaries() or world.canary_hits(t.answer)),
            "external_sends": len(world.external_sends()),
            "session_id": session_id,
            "events": engine.logger.session_events(session_id) if session_id else [],
        }
    finally:
        world.cleanup()


def _safe(obj: Any, world: World) -> Any:
    """Never echo canary values to the browser: mask them (the leak itself is reported as a flag)."""
    if isinstance(obj, dict):
        return {k: _safe(v, world) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe(v, world) for v in obj]
    text = str(obj)
    for v in world.canaries.values():
        text = text.replace(v, "[CANARY]")
    return text[:2000]
