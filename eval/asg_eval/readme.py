"""Insert the headline results from the latest evaluation summary into README.md (between RESULTS markers),
so the README never carries hand-typed numbers. Usage: python -m asg_eval.readme"""

from __future__ import annotations

import json
import re
import sys

from .report import REPORTS, ROOT


def block(s: dict) -> str:
    pc = lambda v: "—" if v is None else f"{v:.1%}"
    c, det = s["claim"], s["content_detection"]
    fp = s["fpr"]["holdout"] or s["fpr"]["dev"]
    iso = s.get("latency_isolated") or {}
    lat = {"p95": iso.get("p95_ms", s["latency_ms"]["fast_path"]["p95"])}
    chans = {k: v for k, v in det["by_channel"].items() if k != "user"}
    docs_n, docs_hit = sum(v["n"] for v in chans.values()), sum(v["detected"] for v in chans.values())
    docs_rec = docs_hit / docs_n if docs_n else None
    user_n = (det["by_channel"].get("user") or {}).get("n", 0)
    user_rec = (det["by_channel"].get("user") or {}).get("recall")
    nd_n = sum(v["n"] for v in det.get("not_delivered", {}).values())
    versions = s["settings"].get("engine_versions", {})
    unfingerprinted = lambda suite: "None" in versions.get(f"e2e_on:{suite}", {"None": 1})
    lines = [f"### Results ({s['date']}, commit `{s['git_sha']}`, generated)", "",
             f"**Grid position by the PRD §15 rule: {c['F']} / {c['D']}** ({c['types_meeting']} of 9 attack types at recall "
             f"≥ 85% with FPR ≤ 5%). The self-declaration is the team's decision, made from these numbers.", "",
             "| Metric | Result |", "|---|---|",
             f"| Detection recall, third-party content ({docs_n} generated attacks through {len(det['by_channel']) - 1} document/data channels"
             + (f"; {nd_n} payloads the channel could not deliver excluded" if nd_n else "") + f") | {pc(docs_rec)} |",
             f"| Detection recall, direct user-turn attacks ({user_n} cases) | {pc(user_rec)} |",
             f"| False-positive rate, {'held-out' if s['fpr']['holdout'] else 'development'} hard-benign set ({fp['n'] if fp else 0} cases) | {pc(fp['fpr'] if fp else None)} |",
             f"| Fast-path latency p95 (isolated) | {lat['p95']} ms |"]
    for e in s["e2e"]:
        note = " · protected run from the 5 Oct engine (before fingerprinting); rerun pending" if unfingerprinted(e["suite"]) else ""
        lines.append(f"| Attack success on the reference agent, `{e['suite']}` suite ({e['off']['scored']} / {e['on']['scored']} scored tests): off → on | "
                     f"{pc(e['off']['asr'])} → {pc(e['on']['asr'])} (canary leaks with protection: {e['canary_leaks_on']}){note} |")
    if s["utility"]:
        lines.append(f"| Benign task utility retained | {pc(s['utility']['retention'])} |")
    priced = [e for e in s["e2e"] if (e.get("overhead") or {}).get("cost_ratio") is not None]
    for e in priced:
        o = e["overhead"]
        lines.append(f"| Security cost per agent cost, `{e['suite']}` suite ({o['runs']} protected runs, list prices) | "
                     f"{o['cost_ratio']:.0%} (security tokens per agent token: {o['token_ratio']}) |")
    lines += ["", "Per-type and per-channel numbers, false alarms and method: [docs/EVALUATION.md](docs/EVALUATION.md)."]
    return "\n".join(lines)


def main() -> None:
    files = sorted(REPORTS.glob("*-summary.json"))
    if not files:
        sys.exit("no summary yet: run python -m asg_eval.summary")
    s = json.loads(files[-1].read_text(encoding="utf-8"))
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    new = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->",
                 lambda _: "<!-- RESULTS:START -->\n" + block(s) + "\n<!-- RESULTS:END -->", text, flags=re.S)
    readme.write_text(new, encoding="utf-8")
    print("README results updated from", files[-1].name)


if __name__ == "__main__":
    main()
