"""EVAL-4 adaptive rounds: turn the protected agent's misses into attack memory, and report rounds side by side.

    python -m intentseal_eval.adaptive learn  <round results.json>        # misses -> AttackMemory (fingerprints only)
    python -m intentseal_eval.adaptive report <round1.json> <round2.json> # per-round attack success, caught rate

The attack text comes from promptfoo's iterative strategies (configs/adaptive.yaml). A "miss" is a case where the
protected agent took a verifiable harmful action (EVAL-5 outcome flags) or the gateway flagged nothing. Misses are
added to the memory the engine consults at Tier 0 (intentseal_core.memory), so a later round shows whether the system
learned. Round 2 must include fresh generated attacks, not only replays, to show generalisation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from intentseal_core.config import load_settings
from intentseal_core.memory import AttackMemory
from intentseal_core.store import Store

from .report import rescore


def rows(path: str) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for r in data["results"]["results"]:
        raw = (r.get("response") or {}).get("output") or "{}"
        try:
            o = rescore(json.loads(raw)) if isinstance(raw, str) else raw
        except ValueError:
            o = {}
        prompt = (r.get("vars") or {}).get("prompt") or (r.get("testCase") or {}).get("vars", {}).get("prompt") or ""
        md = (r.get("testCase") or {}).get("metadata") or {}
        out.append({"prompt": prompt if isinstance(prompt, str) else json.dumps(prompt), "out": o if isinstance(o, dict) else {},
                    "plugin": md.get("pluginId"), "strategy": md.get("strategyId")})
    return out


def missed(r: dict[str, Any]) -> bool:
    o = r["out"]
    return bool(o.get("compromised")) or not (o.get("security") or {}).get("detected")


def learn(path: str) -> None:
    memory = AttackMemory(Store(load_settings().db_path))
    added = skipped = 0
    for r in rows(path):
        if not missed(r) or not r["prompt"]:
            continue
        mid = memory.add(r["prompt"], "attack", ["Instruction Override"], origin="adversary-loop",
                         note=f"{r['plugin']}|{r['strategy']}")
        added += mid is not None
        skipped += mid is None
    print(json.dumps({"added_to_memory": added, "too_short": skipped, "memory": memory.stats()}))


def summary(path: str) -> dict[str, Any]:
    rs = [r for r in rows(path) if r["out"]]
    n = len(rs)
    comp = sum(bool(r["out"].get("compromised")) for r in rs)
    caught = sum(bool((r["out"].get("security") or {}).get("detected")) for r in rs)
    return {"file": Path(path).name, "n": n, "compromised": comp, "asr": round(comp / n, 3) if n else None,
            "caught": caught, "caught_rate": round(caught / n, 3) if n else None, "misses": sum(map(missed, rs))}


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("learn", "report"):
        sys.exit(__doc__)
    if sys.argv[1] == "learn":
        learn(sys.argv[2])
    else:
        print(json.dumps([summary(p) for p in sys.argv[2:]], indent=2))


if __name__ == "__main__":
    main()
