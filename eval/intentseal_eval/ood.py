"""Out-of-distribution check: garak probe families that never appear in our suites, sent as typed user messages to
the detection target (eval/garak/ood_target.json). Detected = any decision other than ALLOW. Writes
eval/reports/<date>-ood.json. Usage: python -m intentseal_eval.ood [eval/garak/runs/ood.detect.report.jsonl]"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

from .report import REPORTS, ROOT


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "eval" / "garak" / "runs" / "ood.detect.report.jsonl"
    by: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "detected": 0, "errors": 0})
    seen: set[tuple[str, int]] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e.get("entry_type") != "attempt" or e.get("status") != 2:
            continue
        key = (e.get("probe_classname", "?"), e.get("seq", 0))
        if key in seen:
            continue
        seen.add(key)
        out = e.get("outputs") or [None]
        o = out[0]
        text = (o.get("text") if isinstance(o, dict) else o) or ""
        b = by[key[0]]
        b["n"] += 1
        if text not in ("ALLOW", "NEUTRALISE", "BLOCK", "ESCALATE"):
            b["errors"] += 1
        elif text != "ALLOW":
            b["detected"] += 1
    total_n = sum(v["n"] - v["errors"] for v in by.values())
    total_d = sum(v["detected"] for v in by.values())
    rep = {"date": time.strftime("%Y-%m-%d"), "source": str(path.relative_to(ROOT)), "channel": "user (typed)",
           "note": "garak probe families never used in our suites or development; detected = decision other than ALLOW",
           "probes": {k: {**v, "recall": round(v["detected"] / (v["n"] - v["errors"]), 3) if v["n"] > v["errors"] else None}
                      for k, v in sorted(by.items())},
           "overall": {"n": total_n, "detected": total_d, "recall": round(total_d / total_n, 3) if total_n else None}}
    out = REPORTS / f"{rep['date']}-ood.json"
    out.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(json.dumps(rep["overall"]), "->", out.name)
    for k, v in rep["probes"].items():
        print(f"  {k:55s} {v['detected']}/{v['n'] - v['errors']}  errors {v['errors']}")


if __name__ == "__main__":
    main()
