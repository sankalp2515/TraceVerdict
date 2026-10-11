"""Repeated trials of the attacks that worked: every test that compromised the unprotected agent in an end-to-end
suite (headline, v2e, mt3), re-run N times in each arm on one agent model, so a protected "0" is not one lucky run.

Writes output/<channel>_<suite>.<arm>.rep.plain.yaml for arm in off / on / actions (actions: content checks off, the action
layer and intent contract alone), pointing at one target port per arm. Test content is copied from the generated
suites as data (D-005); nothing is authored here.

    python build_repeat.py [--ports 8792 8793 8794]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

OUT = Path(__file__).parent / "output"
SUITES = ("headline", "v2e", "mt3")


def key(vars_: dict) -> str:
    return hashlib.sha256(json.dumps(vars_ or {}, sort_keys=True).encode()).hexdigest()[:16]


def compromised(suite: str) -> dict[str, set[str]]:
    import sys
    sys.path.insert(0, str(Path(__file__).parents[1]))
    from intentseal_eval.report import rescore
    hits: dict[str, set[str]] = {}
    for f in OUT.glob(f"*.off.{suite}.results.json"):
        ch = f.name.split(".")[0]
        for r in json.loads(f.read_text(encoding="utf-8"))["results"]["results"]:
            raw = (r.get("response") or {}).get("output") or ""
            try:
                o = json.loads(raw)
            except ValueError:
                continue
            if isinstance(o, dict) and "compromised" in o and rescore(o).get("compromised"):
                hits.setdefault(ch, set()).add(key(r.get("vars")))
    return hits


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", nargs=3, type=int, default=[8792, 8793, 8794])
    a = ap.parse_args()
    ports = dict(zip(("off", "on", "actions"), a.ports))
    merged: dict[str, dict] = {}
    for suite in SUITES:
        for ch, keys in compromised(suite).items():
            src = OUT / f"{ch}.off.{suite}.plain.yaml"
            cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
            tests = [t for t in cfg["tests"] if key(t.get("vars")) in keys]
            for t in tests:
                t.setdefault("metadata", {})["repeatOf"] = suite
            merged[f"{ch}_{suite}"] = cfg | {"tests": tests}   # one file per suite: request bodies differ
    total = 0
    for ch, cfg in merged.items():
        for arm, port in ports.items():
            c = json.loads(json.dumps(cfg))
            t = (c.get("targets") or c["providers"])[0]   # older suites name it "providers"
            t["config"]["url"] = f"http://127.0.0.1:{port}/run"
            t["config"]["body"]["protection"] = arm
            t["label"] = f"agent-{ch}-{arm}-rep"
            c["description"] = f"repeated trials: attacks that compromised the unprotected agent, {ch} channel, protection {arm}"
            (OUT / f"{ch}.{arm}.rep.plain.yaml").write_text(yaml.safe_dump(c, sort_keys=False, allow_unicode=True), encoding="utf-8")
        total += len(cfg["tests"])
        print(ch, len(cfg["tests"]), "tests")
    print("total", total, "attacks x 3 arms")


if __name__ == "__main__":
    main()
