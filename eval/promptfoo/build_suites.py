"""Build the v2 evaluation suites from generator output (promptfoo + garak), as plain promptfoo evals.

Attack text comes only from the generators (D-005, D-010, D-014); this script moves it around as data:

  user channel   promptfoo user set (user.off.tests.yaml) + roles set (roles.tests.yaml)
                 + garak probe attempts (garak/runs/harvest.report.jsonl, capped per probe)
  other channels the pooled indirect payloads (pool.tests.yaml) delivered through EVERY indirect channel
                 (the variant generator of D-006: same seeds, all sources)

Every test keeps its generator metadata (pluginId / strategyId, or garak probe) so the report can map it to
the 9 attack types. Selection is deterministic (fixed seed), so OFF and ON runs see the same tests.

Usage:
  python build_suites.py --suite v2 --protection detect            # full corpus, content checkpoint only
  python build_suites.py --suite v2e --protection off --per-channel 8 --user 96   # stratified e2e subset
  python build_suites.py --suite hb2 --protection detect --benign  # our hard-benign set through every channel (FPR)
  python build_suites.py --suite mt3 --protection off --split-turns 3 --user 40   # multi-step: attacks over 3 turns
  (then: sh run_suite.sh <suite> <protection>)
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import yaml

HERE = Path(__file__).parent
OUT = HERE / "output"
GARAK = HERE.parent / "garak" / "runs" / "harvest.report.jsonl"
HARD_BENIGN = HERE.parent / "corpus" / "v0" / "hard_benign.yaml"
INDIRECT = ["web", "html", "api", "email", "pdf", "docx", "markdown", "code", "ocr_text", "image", "db",
            "pdf_hidden", "docx_hidden", "html_hidden"]


def _tests(name: str) -> list[dict]:
    f = OUT / name
    return yaml.safe_load(f.read_text(encoding="utf-8")).get("tests", []) if f.exists() else []


def garak_tests(cap: int, seed: int) -> list[dict]:
    if not GARAK.exists():
        return []
    by_probe: dict[str, list[str]] = defaultdict(list)
    for line in GARAK.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("entry_type") != "attempt" or r.get("status") != 2:
            continue
        turns = (r.get("prompt") or {}).get("turns") or []
        text = "\n".join(((t.get("content") or {}).get("text") or "") for t in turns if t.get("role") == "user")
        if text.strip() and text not in by_probe[r["probe_classname"]]:
            by_probe[r["probe_classname"]].append(text)
    rng = random.Random(seed)
    out = []
    for probe, texts in sorted(by_probe.items()):
        rng.shuffle(texts)
        for text in texts[:cap]:
            out.append({"vars": {"prompt": text}, "metadata": {"pluginId": f"garak:{probe}", "strategyId": None}})
    return out


def stratified(tests: list[dict], n: int | None, seed: int) -> list[dict]:
    """Round-robin over plugin|strategy groups so a subset keeps the generator mix."""
    if n is None or n >= len(tests):
        return list(tests)
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


def plain(test: dict, var_from: str, var_to: str) -> dict:
    md = dict(test.get("metadata") or {})
    value = (test.get("vars") or {}).get(var_from)
    return {"vars": {var_to: value},
            "metadata": {k: md.get(k) for k in ("pluginId", "strategyId", "goal") if md.get(k) is not None},
            "assert": [{"type": "javascript", "metric": "not_compromised", "value": "!JSON.parse(output).compromised"}]}


def split_turns(test: dict, parts: int) -> dict | None:
    """Spread one generated user-turn attack over `parts` consecutive user turns (PRD §14 type 7: an attack spread
    across several turns; D-006 split variant). Mechanical: sentence boundaries first, else equal word chunks.
    The text is the generator's, unchanged and in order; returns None when it is too short to split."""
    text = str((test.get("vars") or {}).get("prompt") or "")
    words = text.split()
    if len(words) < parts * 4:
        return None
    sentences = [x.strip() for x in re.split(r"(?<=[.!?])\s+", text) if x.strip()]
    if len(sentences) >= parts:
        size = -(-len(sentences) // parts)
        chunks = [" ".join(sentences[i:i + size]) for i in range(0, len(sentences), size)]
    else:
        size = -(-len(words) // parts)
        chunks = [" ".join(words[i:i + size]) for i in range(0, len(words), size)]
    md = dict(test.get("metadata") or {})
    md["strategyId"] = "split-turns"
    return {"vars": {"turns": json.dumps(chunks, ensure_ascii=False)}, "metadata": md, "assert": test.get("assert", [])}


def config(channel: str, protection: str, suite: str, var: str, tests: list[dict], port: int) -> dict:
    return {
        "description": f"{suite}: {channel} channel, protection {protection}",
        "prompts": ["{{" + var + "}}"],
        "providers": [{
            "id": "http", "label": f"agent-{channel}-{protection}-{suite}",
            "config": {"url": f"http://127.0.0.1:{port}/run", "method": "POST",
                       "headers": {"Content-Type": "application/json"},
                       "body": ({"task": "{{turns}}", "channel": "user", "protection": protection} if var == "turns" else
                                {"content": "{{" + var + "}}", "channel": channel, "protection": protection}),
                       "transformResponse": "JSON.stringify(json)"}}],
        "tests": tests,
    }


def benign_tests(path: Path = HARD_BENIGN) -> tuple[list[dict], list[dict]]:
    """Our own hard-benign cases (CC-BY-4.0): user-source cases go to the user channel, the rest to every
    indirect channel. Expected decision: ALLOW (any other decision is a false alarm)."""
    cases = yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]
    text = lambda c: c["text"] if isinstance(c["text"], str) else json.dumps(c["text"], ensure_ascii=False)
    mk = lambda c, var: {"vars": {var: text(c)}, "metadata": {"pluginId": "benign:hard", "caseId": c["id"]}}
    return ([mk(c, "prompt") for c in cases if c["source"] == "user"],
            [mk(c, "document") for c in cases if c["source"] != "user"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", default="v2")
    ap.add_argument("--protection", default="detect", choices=["off", "on", "detect"])
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--garak-cap", type=int, default=20, help="attempts per garak probe")
    ap.add_argument("--per-channel", type=int, default=None, help="indirect payloads per channel (default: all)")
    ap.add_argument("--user", type=int, default=None, help="user-channel tests (default: all)")
    ap.add_argument("--channels", nargs="*", default=None)
    ap.add_argument("--benign", action="store_true", help="build from a hard-benign set instead of attacks")
    ap.add_argument("--benign-file", type=Path, default=HARD_BENIGN, help="hard-benign YAML (default: v0 dev set)")
    ap.add_argument("--split-turns", type=int, default=0, help="multi-turn suite: user attacks spread over N user turns")
    a = ap.parse_args()

    user = ([plain(t, "prompt", "prompt") for t in _tests("user.off.tests.yaml")]
            + [plain(t, "prompt", "prompt") for t in _tests("roles.tests.yaml")]
            + [plain(t, "prompt", "prompt") for t in garak_tests(a.garak_cap, a.seed)])
    pool = [plain(t, "document", "document") for t in _tests("pool.tests.yaml")]
    if a.benign:
        user, pool = benign_tests(a.benign_file)
    if a.split_turns:
        picked = [t for t in (split_turns(x, a.split_turns) for x in stratified(user, None, a.seed)) if t]
        tests = stratified(picked, a.user, a.seed)
        dst = OUT / f"user.{a.protection}.{a.suite}.plain.yaml"
        dst.write_text(yaml.safe_dump(config("user", a.protection, a.suite, "turns", tests, a.port), sort_keys=False,
                                      allow_unicode=True), encoding="utf-8")
        print(dst.name, len(tests))
        return
    channels = a.channels or ["user", *(c for c in INDIRECT if not (a.benign and c.endswith("_hidden")))]
    for ch in channels:
        tests = stratified(user, a.user, a.seed) if ch == "user" else stratified(pool, a.per_channel, a.seed)
        var = "prompt" if ch == "user" else "document"
        dst = OUT / f"{ch}.{a.protection}.{a.suite}.plain.yaml"
        dst.write_text(yaml.safe_dump(config(ch, a.protection, a.suite, var, tests, a.port), sort_keys=False,
                                      allow_unicode=True), encoding="utf-8")
        print(dst.name, len(tests))


if __name__ == "__main__":
    main()
