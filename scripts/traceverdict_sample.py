"""Run all three synthetic backend examples without sponsor credentials or frontend.

Run from the repository root after installing the existing packages:
    python scripts/traceverdict_sample.py --output artifacts/traceverdict
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for relative in ("packages/core", "packages/sdk", "services/gateway", "agents"):
    sys.path.insert(0, str(ROOT / relative))

from intentseal_core.decision_model import StaticDecisionModel  # noqa: E402
from intentseal_core.engine import Engine  # noqa: E402
from intentseal_core.policy import AgentPolicy  # noqa: E402
from intentseal_core.store import Store  # noqa: E402
from intentseal_gateway.cases.fixtures import IDS  # noqa: E402
from intentseal_gateway.cases.models import CreateCase  # noqa: E402
from intentseal_gateway.cases.service import CaseService  # noqa: E402


class SampleScorer:
    def score(self, text):
        return 0.0


async def run(output: Path, include_world: bool = False):
    output.mkdir(parents=True, exist_ok=True)
    engine = Engine(store=Store(output / "sample.db"), classifiers=[SampleScorer()],
                    decision_model=StaticDecisionModel(0), policy_loader=lambda agent: AgentPolicy(agent=agent))
    svc = CaseService(engine)
    try:
        for fid in IDS:
            req = CreateCase(agent_id="research-agent", fixture_id=fid, execution_mode="sample",
                             idempotency_key="example-v4-" + fid)
            case = svc.create(req, "default")
            if case["status"] == "COLLECTING":
                await svc.investigate(case)
            case = svc.world.load(case["case_id"], "default")
            for c in case["candidates"]:
                if c["candidate_id"] not in case["validations"]:
                    await svc.validate(svc.world.load(case["case_id"], "default"), c["candidate_id"])
            case = svc.world.load(case["case_id"], "default")
            report = svc.export(case)
            (output / f"{fid}.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            if include_world:
                (output / f"{fid}-world.json").write_text(json.dumps(case, indent=2, ensure_ascii=False), encoding="utf-8")
            print(json.dumps({"fixture": fid, "mode": "sample", "status": case["status"], "revisions": case["revisions"],
                              "repairs": [{"candidate_id": c["candidate_id"],
                                           "status": case["validations"][c["candidate_id"]]["status"],
                                           "counts": case["validations"][c["candidate_id"]]["counts"]} for c in case["candidates"]]}))
            if case["status"] != "AWAITING_REVIEW":
                raise RuntimeError("sample did not reach its expected bounded validation outcome")
    finally:
        await svc.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "traceverdict")
    parser.add_argument("--include-world", action="store_true", help="also export the complete versioned world aggregate")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.include_world))
