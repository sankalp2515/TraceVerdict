"""False-positive rate on the hard-benign set (G3): legitimate content that looks suspicious.

Each case goes straight through Engine.inspect with its channel; any decision other than ALLOW is a false alarm.
Usage: python -m intentseal_eval.fpr
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import yaml

from intentseal import Guard

ROOT = Path(__file__).resolve().parents[2]
SOURCE_MAP = {"ocr_text": "ocr_text", "docx": "docx", "pdf": "pdf"}


async def run() -> dict:
    cases = yaml.safe_load((ROOT / "eval/corpus/v0/hard_benign.yaml").read_text(encoding="utf-8"))["cases"]
    guard = Guard("research-agent")
    rows = []
    for c in cases:
        s = guard.engine.start_session("research-agent", user_ref="fpr", task="")
        t0 = time.perf_counter()
        text = c["text"] if isinstance(c["text"], str) else json.dumps(c["text"], ensure_ascii=False)   # YAML mappings
        r = await guard.engine.inspect(text, c["source"], "research-agent", session_id=s.session_id, fmt="text")
        rows.append({"id": c["id"], "source": c["source"], "decision": r.decision.value, "rule": r.policy_rule,
                     "tier": r.tier, "degraded": r.degraded, "ms": round((time.perf_counter() - t0) * 1000)})
    fp = [r for r in rows if r["decision"] != "ALLOW"]
    out = {"n": len(rows), "false_alarms": len(fp), "fpr": round(len(fp) / len(rows), 3),
           "escalated": sum(r["tier"] == 2 for r in rows), "rows": rows}
    dst = ROOT / "data" / "eval_runs" / "fpr.hard_benign.json"
    dst.write_text(json.dumps(out, indent=2))
    return out


def main() -> None:
    out = asyncio.run(run())
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}))
    for r in out["rows"]:
        if r["decision"] != "ALLOW":
            print("  false alarm:", r)


if __name__ == "__main__":
    main()
