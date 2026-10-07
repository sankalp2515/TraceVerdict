"""Fast-path latency in isolation (G7): one process, no other load, local classifier, no AI judge involved.

Every inspection is first-seen content (no scan cache), measured inside Engine.inspect. Inputs: our benign sets
and fixture documents as user turns (user turns stay on the fast path in every policy).
Usage: python -m intentseal_eval.latency  ->  data/eval_runs/latency.json
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import yaml

from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.policy import load_policy
from intentseal_core.store import Store
from intentseal.guard import _warm_up

ROOT = Path(__file__).resolve().parents[2]


def texts() -> list[str]:
    out = []
    for f in ("eval/corpus/v0/hard_benign.yaml", "eval/corpus/v1/hard_benign_holdout.yaml"):
        for c in yaml.safe_load((ROOT / f).read_text(encoding="utf-8"))["cases"]:
            out.append(c["text"] if isinstance(c["text"], str) else json.dumps(c["text"]))
    for f in (ROOT / "agents/research_agent/fixtures/workspace").rglob("*"):
        if f.suffix in (".md", ".txt", ".py"):
            out.append(f.read_text(encoding="utf-8"))
    return out


async def run() -> dict:
    _warm_up()
    policy = load_policy("research-agent")
    e = Engine(policy_loader=lambda _: policy, decision_model=StaticDecisionModel(0.0), store=Store(":memory:"))
    ms, tiers = [], []
    for t in texts():
        t0 = time.perf_counter()
        r = await e.inspect(t, "user", policy.agent)
        ms.append((time.perf_counter() - t0) * 1000)
        tiers.append(r.tier)
    fast = sorted(m for m, t in zip(ms, tiers) if t < 2)
    pct = lambda v, q: round(v[min(len(v) - 1, int(q * len(v)))], 1) if v else None
    return {"n": len(fast), "p50_ms": pct(fast, 0.5), "p95_ms": pct(fast, 0.95), "max_ms": round(max(fast), 1) if fast else None,
            "note": "single process, local CPU, first-seen content, Tier 0/1 only"}


def main() -> None:
    out = asyncio.run(run())
    (ROOT / "data" / "eval_runs" / "latency.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out))


if __name__ == "__main__":
    main()
