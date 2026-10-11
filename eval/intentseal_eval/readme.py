"""Insert the headline results from the latest evaluation summary into README.md (between RESULTS markers),
so the README never carries hand-typed numbers. Usage: python -m intentseal_eval.readme"""

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
             f"**All {sum(1 for t in c['types'] if (t['recall'] or 0) > 0)} of 9 attack types detected**, recall "
             f"{pc(min(t['recall'] or 0 for t in c['types']))}–{pc(max(t['recall'] or 0 for t in c['types']))} by type "
             f"({c['types_meeting']} of 9 also meet the internal target of recall ≥ 85% with FPR ≤ 5%; "
             f"see [EVALUATION.md](docs/EVALUATION.md)).", "",
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
    for e in s["e2e"][:1]:   # headline suite; a $0 ratio means the security calls ran on unpriced free models
        o = e.get("overhead") or {}
        if o.get("cost_ratio"):
            lines.append(f"| Security cost per agent cost, `{e['suite']}` suite ({o['runs']} protected runs, list prices) | "
                         f"{o['cost_ratio']:.0%} (security tokens per agent token: {o['token_ratio']}) |")
        elif o.get("token_ratio") is not None:
            lines.append(f"| Security tokens per agent token, `{e['suite']}` suite ({o['runs']} protected runs) | {o['token_ratio']} |")
    lines += ["", "Per-type and per-channel numbers, false alarms and method: [docs/EVALUATION.md](docs/EVALUATION.md)."]
    return "\n".join(lines)


def assurance() -> str | None:
    """Intent contracts, the detectors-off arm, paired and repeated runs, the red-team loop (D-064..D-067)."""
    latest = lambda kind: (lambda f: (f[-1].name, json.loads(f[-1].read_text(encoding="utf-8"))) if f else (None, {}))(
        sorted(REPORTS.glob(f"*-{kind}.json")))
    (cn, ct), (pn, pr), (rn, rt) = latest("contract"), latest("paired"), latest("redteam")
    if not (ct or pr or rt):
        return None
    ci = lambda v: f"95% CI {v[0]:.0%}–{v[1]:.0%}" if v else ""
    hp = (pr.get("suites") or {}).get("headline") or {}
    a = (hp.get("arms") or {}).get("actions") or {}
    engines = ", ".join(sorted({e for arm in (hp.get("arms") or {}).values() for e in arm.get("engines", [])}))
    lines = [f"### Assurance (generated; engines {engines or '—'})", "", "| Check | Result |", "|---|---|"]
    if a:
        pa = hp.get("paired_off_vs_actions") or {}
        lines.append(f"| **Every detector switched off** (content checks off; the action layer and intent contract alone), "
                     f"`headline` suite on the agent | {a['compromised']} of {a['scored']} attacks succeeded ({ci(a['asr_ci95'])}); "
                     f"of the {pa.get('compromised_unprotected')} attacks that worked unprotected, "
                     f"{(pa.get('prevented_by') or {}).get('stopped-action', 0)} were stopped by a recorded action block |")
    if ct:
        tp, nm = ct["third_party"], ct["named_party"]
        lines.append(f"| Worst case, deterministic, detectors off: every send or fetch the generated third-party attacks demand | "
                     f"{tp['contract']['stopped']} of {tp['actions']} stopped; each by at least "
                     f"{min(int(k) for k in tp['independent_rules'])} independent rules |")
        lines.append(f"| ... when the attacker targets a party the user named (\"Do not email them.\") | intent contract "
                     f"{nm['contract']['stopped']} of {nm['actions']}; the previous rules {nm['intent-terms']['stopped']} of "
                     f"{nm['actions']} |")
        b = ct["benign"]["contract"]
        lines.append(f"| Legitimate sends and writes the user asked for (utility tasks), contract on | {b['allowed']} of {b['actions']} allowed |")
    if hp.get("paired_off_vs_on"):
        po = hp["paired_off_vs_on"]
        lines.append(f"| Paired comparison, `headline` (same attacks, both runs completed) | {po['pairs']} pairs: "
                     f"{po['asr_unprotected']:.0%} → {po['asr_protected']:.0%} ({ci(po['asr_protected_ci95'])} protected) |")
    rep = pr.get("repeated") or {}
    if rep:
        arms = rep["arms"]
        cell = lambda k: (f"{arms[k]['compromised_trials']} of {arms[k]['scored']} trials" if k in arms else "—")
        lines.append(f"| Repeated trials: the {rep['attacks']} attacks that ever compromised the unprotected agent, 3 runs each | "
                     f"off {cell('off')} · on {cell('on')} · detectors off {cell('actions')} compromised |")
    if rt:
        g = rt["regression"]
        lines.append(f"| Red-team and repair loop on the `{rt['suite']}` suite ({rt['failures']} failures) | variants caught "
                     f"{g['dev_variants']['caught']}/{g['dev_variants']['n']}; held-out failures now caught "
                     f"{g['holdout_failures']['now_caught']}/{g['holdout_failures']['n']}; new false alarms "
                     f"{g['benign_dev']['new_false_alarms'] + g['benign_holdout']['new_false_alarms']}/"
                     f"{g['benign_dev']['n'] + g['benign_holdout']['n']}: **{rt['decision']}** |")
    lines += ["", f"Reports: `eval/reports/{cn}`, `{pn}`, `{rn}`. Method: [docs/ASSURANCE.md](docs/ASSURANCE.md)."]
    return "\n".join(lines)


def main() -> None:
    files = sorted(REPORTS.glob("*-summary.json"))
    if not files:
        sys.exit("no summary yet: run python -m intentseal_eval.summary")
    s = json.loads(files[-1].read_text(encoding="utf-8"))
    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    new = re.sub(r"<!-- RESULTS:START -->.*?<!-- RESULTS:END -->",
                 lambda _: "<!-- RESULTS:START -->\n" + block(s) + "\n<!-- RESULTS:END -->", text, flags=re.S)
    extra = assurance()
    if extra and "<!-- ASSURANCE:START -->" in new:
        new = re.sub(r"<!-- ASSURANCE:START -->.*?<!-- ASSURANCE:END -->",
                     lambda _: "<!-- ASSURANCE:START -->\n" + extra + "\n<!-- ASSURANCE:END -->", new, flags=re.S)
    readme.write_text(new, encoding="utf-8")
    print("README results updated from", files[-1].name)


if __name__ == "__main__":
    main()
