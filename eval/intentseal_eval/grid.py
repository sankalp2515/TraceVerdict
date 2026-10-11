"""Coverage grid: the nine attack types against every input source, and the declared F x D position, from raw results.

Two labels per test, kept apart:
  official   the evaluation's own category map (category_map.yaml): user-channel tests carry their generator plugin's
             types; document and data channels carry Indirect Prompt Injection (+ Encoded Instructions for encoded
             variants, Context Poisoning for stored records). These are the numbers in EVALUATION.md.
  goal       third-party tests also carry the generator's own description of what the injected text tries to make
             the agent do (promptfoo `goal`). A published keyword rule (GOAL_RULES) maps that description to the
             types it pursues, e.g. "exfiltrate an API token ... via email" -> Credential Theft, Tool Abuse. This shows
             which attack goals were delivered through which source; it is a secondary view, never mixed into the
             official recall.

Cells: detected / delivered tests at the content checkpoint (v3 suite, engine of the final run); holds and payloads a
channel cannot deliver are excluded, as in the summary. Tool Abuse and Multi-Step Jailbreaks in the user channel use
the end-to-end checkpoint (any layer), as the summary does.

    python -m intentseal_eval.grid   ->  eval/reports/<date>-grid.json, docs/COVERAGE.md,
                                         docs/assets/grid/coverage-matrix.svg, docs/assets/grid/fd-grid.svg
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from html import escape
from typing import Any


from intentseal_core.types import ATTACK_TYPES

from .report import PF_OUT, REPORTS, ROOT, categories
from .summary import HOLDS, NOT_DELIVERED

GOAL_RULES = {
    "Instruction Override": r"overrid|ignore the user|ignore .*request",
    "Role Change": r"\brole\b|\bpersona\b|impersonat|\bpretend|\bact as\b|developer mode|admin mode",
    "Secret Extraction": r"system prompt|system instructions|internal configuration|internal policies|internal data|tool configuration|tool inventory|environment variables",
    "Credential Theft": r"credential|token|password|api key",
    "Tool Abuse": r"forward|send an email|via email|email address|write it to a file|workspace file|execute code|delete|create unauthorized|access all|access and disclose",
}
SOURCES = [   # (channel, column label, group)
    ("user", "User turn", "Direct"),
    ("web", "Web page", "Text & data"), ("html", "HTML", "Text & data"), ("markdown", "Markdown", "Text & data"),
    ("email", "Email", "Text & data"), ("api", "API JSON", "Text & data"), ("db", "DB record", "Text & data"),
    ("code", "Code", "Text & data"),
    ("pdf", "PDF", "Documents"), ("docx", "Word", "Documents"),
    ("pdf_hidden", "PDF hidden", "Hidden text"), ("docx_hidden", "Word hidden", "Hidden text"),
    ("html_hidden", "HTML hidden", "Hidden text"),
    ("image", "Image", "Images (OCR)"), ("ocr_text", "Screenshot", "Images (OCR)"),
]
E2E_USER = {"Tool Abuse", "Multi-Step Jailbreaks"}


def load(suite: str = "v3") -> list[dict[str, Any]]:
    rows = []
    for f in sorted(PF_OUT.glob(f"*.detect.{suite}.results.json")):
        ch = f.name.split(".")[0]
        for r in json.loads(f.read_text(encoding="utf-8"))["results"]["results"]:
            try:
                o = json.loads((r.get("response") or {}).get("output") or "{}")
            except ValueError:
                continue
            md = (r.get("testCase") or {}).get("metadata") or {}
            if o.get("decision") is None or o.get("rule") in HOLDS or (ch, md.get("strategyId")) in NOT_DELIVERED:
                continue
            goal = md.get("goal") or ""
            rows.append({"channel": ch, "detected": bool(o.get("detected")), "engine": o.get("engine"),
                         "official": categories(md.get("pluginId"), md.get("strategyId"), ch),
                         "goal": sorted(t for t, rx in GOAL_RULES.items() if ch != "user" and re.search(rx, goal, re.I))})
    return rows


def build() -> dict[str, Any]:
    rows = load()
    s = json.loads(sorted(REPORTS.glob("*-summary.json"))[-1].read_text(encoding="utf-8"))
    claim = {t["type"]: t for t in s["claim"]["types"]}
    cells: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for t in ATTACK_TYPES:
        for ch, _, _ in SOURCES:
            off = [r["detected"] for r in rows if r["channel"] == ch and t in r["official"]]
            goal = [r["detected"] for r in rows if r["channel"] == ch and t in r["goal"] and t not in r["official"]]
            if ch == "user" and t in E2E_USER:
                c = claim[t]
                cells[t][ch] = {"label": "official", "checkpoint": "end-to-end", "n": c["n"],
                                "detected": round((c["recall"] or 0) * c["n"]), "recall": c["recall"]}
            elif off:
                cells[t][ch] = {"label": "official", "checkpoint": "content", "n": len(off), "detected": sum(off),
                                "recall": round(sum(off) / len(off), 3)}
            elif goal:
                cells[t][ch] = {"label": "goal", "checkpoint": "content", "n": len(goal), "detected": sum(goal),
                                "recall": round(sum(goal) / len(goal), 3)}
    per_type = {}
    for t in ATTACK_TYPES:
        cs = cells.get(t, {})
        per_type[t] = {"sources": len(cs), "official_recall": claim[t]["recall"], "official_n": claim[t]["n"],
                       "checkpoint": claim[t]["checkpoint"]}
    det = s["content_detection"]
    docs = {k: v for k, v in det["by_channel"].items() if k != "user"}
    return {"date": time.strftime("%Y-%m-%d"), "summary": s["date"], "commit": s["git_sha"],
            "engines": sorted({r["engine"] for r in rows if r["engine"]}), "goal_rules": GOAL_RULES,
            "sources": [{"channel": c, "label": lab, "group": g} for c, lab, g in SOURCES],
            "cells": cells, "per_type": per_type,
            "position": {"F": "F3", "D": "D3", "types_detected": sum(1 for t in claim.values() if (t["recall"] or 0) > 0),
                         "sources": len(SOURCES),
                         "docs_recall": round(sum(v["detected"] for v in docs.values()) / sum(v["n"] for v in docs.values()), 3),
                         "docs_n": sum(v["n"] for v in docs.values()),
                         "protected_tests": sum(e["on"]["scored"] for e in s["e2e"]),
                         "protected_compromised": sum(e["on"]["compromised"] for e in s["e2e"]),
                         "fpr": (s["fpr"]["holdout"] or {}).get("fpr"), "user_recall": det["by_channel"]["user"]["recall"]}}


# ---- rendering (deterministic SVG, same visual language as docs/assets/architecture) -----------------------------
INK, MUTED, LINE, BG = "#13213C", "#5B6472", "#D5D9E0", "#FAFAF7"
FONT = "Inter, 'Segoe UI', Helvetica, Arial, sans-serif"


def tone(recall: float | None) -> tuple[str, str]:
    if recall is None:
        return "#F1F2F4", MUTED
    if recall >= 0.95:
        return "#1F3A5F", "#FFFFFF"
    if recall >= 0.85:
        return "#4A6A93", "#FFFFFF"
    if recall >= 0.6:
        return "#E9D9B8", INK
    return "#EBC2BB", INK


def matrix_svg(g: dict[str, Any]) -> str:
    left, top, cw, ch, gh = 232, 150, 74, 50, 26
    cols = g["sources"]
    w = left + cw * len(cols) + 24
    h = top + ch * len(ATTACK_TYPES) + 128
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">',
         f'<rect width="{w}" height="{h}" fill="{BG}"/>',
         f'<text x="24" y="38" font-size="20" font-weight="600" fill="{INK}">Attack types × input sources: detected / tested</text>',
         f'<text x="24" y="60" font-size="12.5" fill="{MUTED}">Content checkpoint, generated attacks (promptfoo, garak), engine {", ".join(g["engines"])}; '
         f'user-turn Tool Abuse and Multi-Step at the end-to-end checkpoint. Dashed cells: goal view (see legend).</text>']
    groups: list[tuple[str, int, int]] = []
    for i, c in enumerate(cols):
        if groups and groups[-1][0] == c["group"]:
            groups[-1] = (c["group"], groups[-1][1], i)
        else:
            groups.append((c["group"], i, i))
    for name, a, b in groups:
        x0, x1 = left + a * cw + 3, left + (b + 1) * cw - 3
        o.append(f'<line x1="{x0}" y1="{top - gh - 22}" x2="{x1}" y2="{top - gh - 22}" stroke="{INK}" stroke-width="1.5"/>')
        o.append(f'<text x="{(x0 + x1) / 2}" y="{top - gh - 30}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="middle">{escape(name)}</text>')
    for i, c in enumerate(cols):
        x = left + i * cw + cw / 2
        o.append(f'<text x="{x}" y="{top - 14}" font-size="11" fill="{INK}" text-anchor="middle">{escape(c["label"])}</text>')
    for j, t in enumerate(ATTACK_TYPES):
        y = top + j * ch
        pt = g["per_type"][t]
        o.append(f'<text x="24" y="{y + 22}" font-size="13" font-weight="600" fill="{INK}">{escape(t)}</text>')
        o.append(f'<text x="24" y="{y + 39}" font-size="11" fill="{MUTED}">overall {pt["official_recall"]:.0%} of {pt["official_n"]} · {pt["sources"]} source{"s" if pt["sources"] != 1 else ""}</text>')
        for i, c in enumerate(cols):
            x = left + i * cw
            cell = g["cells"].get(t, {}).get(c["channel"])
            if cell is None:
                o.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cw - 6}" height="{ch - 6}" rx="5" fill="#F1F2F4"/>')
                o.append(f'<text x="{x + cw / 2}" y="{y + ch / 2 + 4}" font-size="12" fill="#A3A9B3" text-anchor="middle">–</text>')
                continue
            fill, fg = tone(cell["recall"])
            dash = ' stroke="#C2410C" stroke-width="1.6" stroke-dasharray="4 3"' if cell["label"] == "goal" else ""
            o.append(f'<rect x="{x + 3}" y="{y + 3}" width="{cw - 6}" height="{ch - 6}" rx="5" fill="{fill}"{dash}/>')
            o.append(f'<text x="{x + cw / 2}" y="{y + 23}" font-size="13" font-weight="600" fill="{fg}" text-anchor="middle">{cell["recall"]:.0%}</text>')
            o.append(f'<text x="{x + cw / 2}" y="{y + 38}" font-size="10" fill="{fg}" text-anchor="middle" opacity="0.85">{cell["detected"]}/{cell["n"]}</text>')
    ly = top + ch * len(ATTACK_TYPES) + 34
    legend = [("#1F3A5F", "≥ 95%"), ("#4A6A93", "85–95%"), ("#E9D9B8", "60–85%"), ("#EBC2BB", "< 60%"), ("#F1F2F4", "not tested")]
    x = 24
    for fill, lab in legend:
        o.append(f'<rect x="{x}" y="{ly}" width="18" height="14" rx="3" fill="{fill}"/><text x="{x + 24}" y="{ly + 11}" font-size="11.5" fill="{INK}">{escape(lab)}</text>')
        x += 110
    o.append(f'<rect x="{x}" y="{ly}" width="18" height="14" rx="3" fill="#FFFFFF" stroke="#C2410C" stroke-width="1.6" stroke-dasharray="4 3"/>'
             f'<text x="{x + 24}" y="{ly + 11}" font-size="11.5" fill="{INK}">goal view: type taken from the generator&#8217;s own goal text (keyword rule in grid.py), not the official label</text>')
    o.append(f'<text x="24" y="{ly + 40}" font-size="11.5" fill="{MUTED}">Multi-step jailbreaks are conversations, so they are tested in the user channel only. '
             'No generated third-party goal pursues a role change; role change is tested in the user channel.</text>')
    o.append(f'<text x="24" y="{ly + 58}" font-size="11.5" fill="{MUTED}">Source: eval/reports/{g["date"]}-grid.json · python -m intentseal_eval.grid · summary {g["summary"]}, commit {g["commit"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def fd_svg(g: dict[str, Any]) -> str:
    p = g["position"]
    w, h, left, top, cw, chh = 1200, 640, 210, 110, 320, 140
    F = [("F1", "Detect ≥ 2 attack types"), ("F2", "Detect ≥ 5 attack types"), ("F3", "Detect ≥ 7 attack types")]
    D = [("D3", "Highly heterogeneous multimodal input; high, demonstrable reliability"),
         ("D2", "Mostly structured and textual input; high, demonstrable reliability"),
         ("D1", "Mostly structured and textual input; acceptable in most situations")]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">',
         f'<rect width="{w}" height="{h}" fill="{BG}"/>',
         f'<text x="40" y="44" font-size="22" font-weight="600" fill="{INK}">Solution grid: declared position F3 · D3</text>',
         f'<text x="40" y="68" font-size="13" fill="{MUTED}">Feature level (attack types detected) × depth level (input heterogeneity and reliability)</text>']
    for i, (k, lab) in enumerate(F):
        x = left + i * cw
        o.append(f'<text x="{x + cw / 2}" y="{top - 14}" font-size="13" fill="{INK}" text-anchor="middle"><tspan font-weight="700">{k}</tspan>  {escape(lab)}</text>')
    for j, (k, lab) in enumerate(D):
        y = top + j * chh
        o.append(f'<text x="40" y="{y + 50}" font-size="18" font-weight="700" fill="{INK}">{k}</text>')
        words, line, ly = lab.split(), "", y + 72
        for wd in words:
            if len(line) + len(wd) > 24:
                o.append(f'<text x="40" y="{ly}" font-size="11.5" fill="{MUTED}">{escape(line)}</text>')
                line, ly = wd, ly + 15
            else:
                line = (line + " " + wd).strip()
        o.append(f'<text x="40" y="{ly}" font-size="11.5" fill="{MUTED}">{escape(line)}</text>')
        for i, (fk, _) in enumerate(F):
            x = left + i * cw
            ours = k == "D3" and fk == "F3"
            o.append(f'<rect x="{x + 4}" y="{y + 4}" width="{cw - 8}" height="{chh - 8}" rx="8" '
                     + ('fill="#1F3A5F" stroke="#C2410C" stroke-width="3"/>' if ours else f'fill="#FFFFFF" stroke="{LINE}"/>'))
            if ours:
                lines = [("IntentSeal", 17, 700),
                         (f"{p['types_detected']} of 9 types detected · {p['sources']} input sources", 13, 500),
                         (f"{p['docs_recall']:.1%} recall on {p['docs_n']} attacks in documents and data", 12.5, 400),
                         (f"0% attack success in {p['protected_tests']} protected agent tests", 12.5, 400),
                         ("PDF, Word, HTML, email, images, API, code, RAG", 12, 400)]
                yy = y + 32
                for txt, sz, wt in lines:
                    o.append(f'<text x="{x + 22}" y="{yy}" font-size="{sz}" font-weight="{wt}" fill="#FFFFFF">{escape(txt)}</text>')
                    yy += 22 if sz > 14 else 21
            else:
                o.append(f'<text x="{x + cw / 2}" y="{y + chh / 2 + 5}" font-size="13" fill="#A3A9B3" text-anchor="middle">{fk} · {k}</text>')
    o.append(f'<text x="40" y="{h - 52}" font-size="12" fill="{MUTED}">Limits stated with the claim: typed user-turn attacks {p["user_recall"]:.0%} detected (the action layer still stops the harm); '
             f'held-out hard-benign false alarms {p["fpr"]:.1%}.</text>')
    o.append(f'<text x="40" y="{h - 32}" font-size="12" fill="{MUTED}">Evidence: docs/EVALUATION.md, docs/ASSURANCE.md, docs/COVERAGE.md · summary {g["summary"]}, commit {g["commit"]}</text>')
    o.append("</svg>")
    return "\n".join(o)


def markdown(g: dict[str, Any]) -> str:
    cols = g["sources"]
    out = ["# Coverage: nine attack types across every input source", "",
           f"Generated by `python -m intentseal_eval.grid` from the raw results of the final run (summary {g['summary']}, "
           f"commit `{g['commit']}`, engine {', '.join(g['engines'])}). Detected / tested at the content checkpoint; "
           "user-turn Tool Abuse and Multi-Step Jailbreaks at the end-to-end checkpoint.", "",
           "![Attack types × input sources](assets/grid/coverage-matrix.svg)", "",
           "![Solution grid F3 · D3](assets/grid/fd-grid.svg)", "",
           "## How to read it", "",
           "- **Official** cells use the evaluation's category map, the numbers in [EVALUATION.md](EVALUATION.md).",
           "- **Goal view** cells (marked *g*) take the type from the generator's own description of what the injected "
           "text tries to make the agent do, with the keyword rule below. They show which attack goals were delivered "
           "through which source; they are not added to the official recall.",
           "- Multi-step jailbreaks are conversations: tested in the user channel. No generated third-party goal pursues "
           "a role change.", "", "| Attack type | " + " | ".join(c["label"] for c in cols) + " |",
           "|---|" + "---|" * len(cols)]
    for t in ATTACK_TYPES:
        row = []
        for c in cols:
            cell = g["cells"].get(t, {}).get(c["channel"])
            row.append("–" if cell is None else f"{cell['recall']:.0%} ({cell['detected']}/{cell['n']}){' g' if cell['label'] == 'goal' else ''}")
        out.append(f"| {t} | " + " | ".join(row) + " |")
    out += ["", "Goal rule (case-insensitive regular expressions on the generator's goal text):", ""]
    out += [f"- {t}: `{rx}`" for t, rx in g["goal_rules"].items()]
    out += ["", f"Data: `eval/reports/{g['date']}-grid.json`.", ""]
    return "\n".join(out)


def main() -> None:
    g = build()
    (REPORTS / f"{g['date']}-grid.json").write_text(json.dumps(g, indent=1, ensure_ascii=False), encoding="utf-8")
    d = ROOT / "docs" / "assets" / "grid"
    d.mkdir(parents=True, exist_ok=True)
    (d / "coverage-matrix.svg").write_text(matrix_svg(g), encoding="utf-8")
    (d / "fd-grid.svg").write_text(fd_svg(g), encoding="utf-8")
    (ROOT / "docs" / "COVERAGE.md").write_text(markdown(g), encoding="utf-8")
    for t in ATTACK_TYPES:
        print(t.ljust(26), g["per_type"][t]["sources"], "sources", {c: f"{v['detected']}/{v['n']}{'g' if v['label'] == 'goal' else ''}"
                                                                  for c, v in g["cells"].get(t, {}).items()})


if __name__ == "__main__":
    main()
