"""Repeat a declared local task-routing suite through two discovered NVIDIA Nightshift routes.

This is a small development evaluation, not an external benchmark or a safety certification.
Every result and provider error is retained. It never changes application model settings.
"""
import asyncio
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import statistics
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
for source in ("packages/core", "services/gateway", "agents"):
    sys.path.insert(0, str(ROOT / source))
from intentseal_core.config import load_env  # noqa: E402
from intentseal_core.policy import AgentPolicy  # noqa: E402
from intentseal_gateway.cases.agent_replay import run_agent_suite  # noqa: E402
from intentseal_gateway.cases.fixtures import fixture, IDS  # noqa: E402
from intentseal_gateway.cases.integrations import Nightshift  # noqa: E402
from intentseal_gateway.cases.models import digest  # noqa: E402
from intentseal_gateway.cases.replay_build import replay_build_sha256  # noqa: E402


async def main():
    load_env()
    routes = ["nvidia/nemotron-3.5-lightning-30b-a3b", "nvidia/nemotron-3-ultra-550b-a55b"]
    selected = {"unauthorized-contact", "authorized-send", "authorized-ops", "benign-summary"}
    result = {"captured_at": datetime.now(timezone.utc).isoformat(), "repeats": 2,
              "replay_build_sha256": replay_build_sha256(), "scenario_ids": sorted(selected),
              "scope": "Same 12 development tasks per route, repeated twice. Synthetic documents, real Nightshift calls, local-only tools.",
              "limitations": ["Development prompts informed implementation; no untouched external benchmark.",
                              "Resisted unsafe tasks are model behavior, not control-effect proof.",
                              "Deterministic artifact/summary marker, not generated prose quality.",
                              "Two repetitions cannot establish broad stochastic robustness."], "routes": []}
    async with httpx.AsyncClient() as client:
        models = Nightshift(client)
        discovered = {x["id"] for x in await models.discover()}
        for route in routes:
            if route not in discovered:
                raise ValueError("Required comparison route not discovered")
            os.environ["METERLESS_REPLAY_MODEL"] = route
            runs = []
            for repetition in range(2):
                for fid in IDS:
                    frozen = fixture(fid, "evaluation-agent", "default")
                    frozen["scenarios"] = [s for s in frozen["scenarios"] if s["id"] in selected]
                    outcomes = await run_agent_suite(models, AgentPolicy.model_validate(frozen["policy"]), frozen)
                    runs.append({"fixture": fid, "repetition": repetition + 1, "input_manifest_sha256": digest(frozen), "outcomes": outcomes})
                    print(json.dumps({"route": route, "fixture": fid, "repetition": repetition + 1,
                                      "outcomes": dict(Counter(t["outcome"] for t in outcomes))}), flush=True)
            trials = [t for run in runs for t in run["outcomes"]]
            receipts = [p for t in trials for p in t["model_calls"]]
            latency = sorted(p["duration_ms"] for p in receipts)
            entry = {"requested_route": route, "runs": runs, "summary": {
                "total_trials": len(trials), "outcomes": dict(Counter(t["outcome"] for t in trials)),
                "utility": dict(Counter(t["outcome"] for t in trials if t["category"] == "utility")),
                "unsafe": dict(Counter(t["outcome"] for t in trials if t["category"] == "unsafe")),
                "successful_call_p50_ms": statistics.median(latency) if latency else None,
                "successful_call_p95_ms": latency[min(len(latency)-1, int(.95*len(latency)))] if latency else None,
                "returned_models": sorted({p.get("actual_model_evidence") or "unattributed" for p in receipts}),
                "reported_input_tokens": sum(p.get("input_tokens") or 0 for p in receipts),
                "reported_output_tokens": sum(p.get("output_tokens") or 0 for p in receipts)}}
            result["routes"].append(entry)
            output = ROOT / "examples/traceverdict/nemotron-evaluation.json"
            output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"summaries": [{"route": r["requested_route"], **r["summary"]} for r in result["routes"]]}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
