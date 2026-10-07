"""Benign end-to-end suite (utility, G3b): our own tasks with deterministic checks.

Usage: python -m intentseal_eval.benign [--protection off|on] [--role agent_eval]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

import yaml

from intentseal_core.llm.router import Router
from research_agent import ResearchAgent, World

ROOT = Path(__file__).resolve().parents[2]
logging.getLogger("httpx").setLevel(logging.WARNING)


def check(spec: dict[str, Any], answer: str, world: World) -> bool:
    a = answer.lower()
    sent = world.outbox
    ok = True
    if "answer_contains" in spec:
        ok &= all(str(x).lower() in a for x in spec["answer_contains"])
    if "answer_contains_any" in spec:
        ok &= any(str(x).lower() in a for x in spec["answer_contains_any"])
    if "sent_to" in spec:
        ok &= any(m.get("to", "").strip().lower() == spec["sent_to"].lower() for m in sent)
    if "sent_body_contains" in spec:
        ok &= any(all(str(x).lower() in (m.get("body", "") + m.get("subject", "")).lower()
                      for x in spec["sent_body_contains"]) for m in sent)
    if "sent_body_contains_any" in spec:
        ok &= any(any(str(x).lower() in (m.get("body", "") + m.get("subject", "")).lower()
                      for x in spec["sent_body_contains_any"]) for m in sent)
    if "wrote_file" in spec:
        ok &= any(w["path"].replace("\\", "/").lstrip("./") == spec["wrote_file"] for w in world.writes)
    return bool(ok)


async def run_suite(protection: str = "off", role: str = "agent_eval", hooks_factory=None,
                    only: list[str] | None = None) -> dict[str, Any]:
    tasks = yaml.safe_load((ROOT / "eval/corpus/v0/benign_tasks.yaml").read_text(encoding="utf-8"))["tasks"]
    if only:
        tasks = [t for t in tasks if t["id"] in only]
    router = Router()
    rows = []
    for t in tasks:
        world = World()
        t0 = time.perf_counter()
        hooks = hooks_factory(world, t["task"]) if hooks_factory else None
        tr = await ResearchAgent(router, world, hooks=hooks, role=role).run(t["task"])
        rows.append({"id": t["id"], "channel": t["channel"], "ok": (not tr.error) and check(t["check"], tr.answer, world),
                     "error": bool(tr.error), "blocked_tools": [e["tool"] for e in tr.tool_calls() if not e["allowed"]],
                     "seconds": round(time.perf_counter() - t0, 1), "model": tr.providers[-1] if tr.providers else None})
        world.cleanup()
    await router.aclose()
    done = [r for r in rows if not r["error"]]
    return {"protection": protection, "role": role, "n": len(rows), "errors": len(rows) - len(done),
            "success_rate": round(sum(r["ok"] for r in done) / max(1, len(done)), 3), "rows": rows}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protection", default="off")
    ap.add_argument("--role", default="agent_eval")
    ap.add_argument("--only", nargs="*", help="task ids to run")
    a = ap.parse_args()
    factory = None
    if a.protection == "on":
        from intentseal_eval.protection import guard_hooks
        factory = guard_hooks
    res = asyncio.run(run_suite(a.protection, a.role, factory, a.only))
    out = ROOT / "data" / "eval_runs" / f"benign.{a.protection}.{a.role}{'.subset' if a.only else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}))
    for r in res["rows"]:
        if not r["ok"]:
            print("  fail:", r["id"], r["channel"], "error" if r["error"] else "", r["model"])


if __name__ == "__main__":
    main()
