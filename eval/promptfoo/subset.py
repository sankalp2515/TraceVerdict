"""Pick a fixed, stratified subset of already-generated tests (by plugin/strategy metadata) and point it
at a given target port and protection mode. Same seed + same source files => the same tests in both modes.

Usage: python subset.py --name headline --port 8788 --protection off --take user=24 email=2 web=2 pdf=2
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent / "output"


def pick(tests: list[dict], n: int, seed: int) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for t in tests:
        md = t.get("metadata") or {}
        groups[f"{md.get('pluginId')}|{md.get('strategyId')}"].append(t)
    rng = random.Random(seed)
    for g in groups.values():
        rng.shuffle(g)
    keys = sorted(groups)
    rng.shuffle(keys)
    out: list[dict] = []
    while len(out) < n and any(groups.values()):
        for k in keys:
            if groups[k] and len(out) < n:
                out.append(groups[k].pop())
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="headline")
    ap.add_argument("--port", type=int, default=8788)
    ap.add_argument("--protection", default="off")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--take", nargs="+", default=["user=24", "email=2", "web=2", "pdf=2"])
    a = ap.parse_args()
    for spec in a.take:
        ch, n = spec.split("=")
        src = HERE / f"{ch}.off.plain.yaml"          # tests were generated once; mode is set on the target
        cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
        cfg["tests"] = pick(cfg["tests"], int(n), a.seed)
        for t in cfg.get("targets", []):
            t["config"]["url"] = f"http://127.0.0.1:{a.port}/run"
            t["config"]["body"]["protection"] = a.protection
            t["label"] = f"agent-{ch}-{a.protection}-{a.name}"
        dst = HERE / f"{ch}.{a.protection}.{a.name}.plain.yaml"
        dst.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(dst.name, len(cfg["tests"]))


if __name__ == "__main__":
    main()
