"""Deterministic SVG architecture diagrams for docs/assets/architecture (no rendering dependency).

The structure of each diagram (its boxes and connectors) is also kept as Mermaid in docs/diagrams/*.mmd, which GitHub
renders natively; this file adds the presentation layout: explicit positions, orthogonal connectors, trust
boundaries and one visual language across all diagrams. Change a diagram here and in its .mmd together, then:

    python docs/diagrams/build.py            # writes docs/assets/architecture/{system-context,components,provenance,evaluation}.svg
    sh docs/diagrams/render.sh               # writes docs/assets/architecture/runtime-sequence.svg (Mermaid)

Every box and connector maps to docs/diagrams/INVENTORY.md, which names the source files that verify it.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "architecture"
FONT = "Arial, Helvetica, sans-serif"
BG, INK, MUTED, LINE = "#FAFAF7", "#13213C", "#5B6472", "#4B5563"

STYLE = {   # kind: fill, stroke, text, sub-text, stroke width, dash
    "untrusted": ("#FFF4EB", "#C2410C", "#7C2D12", "#9A3412", 1.6, "5 4"),
    "external": ("#FFFFFF", "#6B7280", "#1F2937", "#4B5563", 1.3, None),
    "trusted": ("#E8EDF5", "#1F3A5F", "#13213C", "#3B4A63", 1.4, None),
    "ai": ("#F4F6FA", "#4A6A93", "#13213C", "#3B4A63", 1.4, "2 3"),
    "enforce": ("#1F3A5F", "#C2410C", "#FFFFFF", "#D6DEEA", 2.6, None),
    "store": ("#F3F4F6", "#4B5563", "#13213C", "#4B5563", 1.3, None),
    "allow": ("#EAF3EE", "#2F6B4F", "#1D4333", "#2F6B4F", 1.6, None),
    "block": ("#F9E7E5", "#9B1C1C", "#7F1D1D", "#9B1C1C", 1.6, None),
    "hold": ("#FDF3E1", "#B7791F", "#744210", "#975A16", 1.6, None),
}
ZONE = {   # kind: fill, stroke, label colour, width, dash
    "seal": ("#EEF2F8", "#1F3A5F", "#1F3A5F", 2.0, None),
    "untrusted": ("#FFFBF7", "#C2410C", "#9A3412", 1.6, "7 5"),
    "plain": ("#FFFFFF", "#9AA3AF", "#4B5563", 1.2, None),
    "external": ("#FAFAF7", "#9AA3AF", "#4B5563", 1.2, "3 4"),
}


class Diagram:
    def __init__(self, w: int, h: int, title: str, subtitle: str) -> None:
        self.w, self.h = w, h
        self.back: list[str] = []
        self.mid: list[str] = []
        self.front: list[str] = []
        self.front.append(f'<text x="40" y="44" font-size="22" font-weight="700" fill="{INK}">{escape(title)}</text>')
        self.front.append(f'<text x="40" y="68" font-size="13.5" fill="{MUTED}">{escape(subtitle)}</text>')
        self.boxes: dict[str, tuple[float, float, float, float]] = {}

    # ---- shapes ------------------------------------------------------------------------------------------------
    def zone(self, x: float, y: float, w: float, h: float, label: str, kind: str = "plain", at: str = "top") -> None:
        """A trust boundary. `at`: where the label sits (top or bottom, left-aligned), chosen so no connector crosses it."""
        fill, stroke, col, sw, dash = ZONE[kind]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.back.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
        ly = y + 22 if at == "top" else y + h - 11
        self.back.append(f'<text x="{x + 16}" y="{ly}" font-size="11.5" font-weight="700" letter-spacing="1.2" fill="{col}">{escape(label.upper())}</text>')

    def box(self, key: str, x: float, y: float, w: float, h: float, title: str, sub: str | list[str] = "",
            kind: str = "trusted", tag: str = "", size: float = 15) -> None:
        fill, stroke, col, subcol, sw, dash = STYLE[kind]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.boxes[key] = (x, y, w, h)
        if kind == "store" and h >= 80:   # cylinder only where it has room; smaller records are plain store boxes
            e = 9
            self.mid.append(f'<path d="M{x},{y + e} a{w / 2},{e} 0 0,0 {w},0 a{w / 2},{e} 0 0,0 {-w},0 v{h - 2 * e} '
                            f'a{w / 2},{e} 0 0,0 {w},0 v{-(h - 2 * e)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            top = y + 2 * e
        else:
            self.mid.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
            top = y
        subs = [sub] if isinstance(sub, str) else sub
        subs = [s for s in subs if s]
        lines = 1 + len(subs)
        cy = top + (y + h - top) / 2 - (lines - 1) * 8.5
        self.front.append(f'<text x="{x + w / 2}" y="{cy + 5}" font-size="{size}" font-weight="700" fill="{col}" text-anchor="middle">{escape(title)}</text>')
        for i, s in enumerate(subs):
            self.front.append(f'<text x="{x + w / 2}" y="{cy + 5 + 18 * (i + 1)}" font-size="12.5" fill="{subcol}" text-anchor="middle">{escape(s)}</text>')
        if tag:
            self.front.append(f'<text x="{x + 10}" y="{y + 15}" font-size="10" font-weight="700" letter-spacing="0.8" fill="{subcol}">{escape(tag)}</text>')

    def diamond(self, key: str, cx: float, cy: float, r: float, title: str) -> None:
        fill, stroke, col, _, sw, _ = STYLE["enforce"]
        self.boxes[key] = (cx - r, cy - r, 2 * r, 2 * r)
        self.mid.append(f'<polygon points="{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
        self.front.append(f'<text x="{cx}" y="{cy + 5}" font-size="14" font-weight="700" fill="{col}" text-anchor="middle">{escape(title)}</text>')

    def text(self, x: float, y: float, s: str, size: float = 12.5, color: str = MUTED, anchor: str = "start",
             weight: int = 400) -> None:
        self.front.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>')

    # ---- connectors --------------------------------------------------------------------------------------------
    def arrow(self, pts: list[tuple[float, float]], label: str = "", at: int = 0, dx: float = 0, dy: float = -7,
              anchor: str = "middle", dashed: bool = False, color: str = LINE, head: bool = True) -> None:
        d = "M" + " L".join(f"{x},{y}" for x, y in pts)
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        mk = ' marker-end="url(#ah)"' if head else ""
        self.mid.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.6"{dash}{mk}/>')
        if label:
            (x1, y1), (x2, y2) = pts[at], pts[at + 1]
            lx, ly = (x1 + x2) / 2 + dx, (y1 + y2) / 2 + dy
            wid = len(label) * 6.4 + 10
            bx = lx - wid / 2 if anchor == "middle" else (lx - 5 if anchor == "start" else lx - wid + 5)
            self.front.append(f'<rect x="{bx}" y="{ly - 12}" width="{wid}" height="16" fill="{BG}" opacity="0.92"/>')
            self.front.append(f'<text x="{lx}" y="{ly}" font-size="12.5" fill="#374151" text-anchor="{anchor}">{escape(label)}</text>')

    def legend(self, y: float, items: list[tuple[str, str]], note: str = "") -> None:
        x = 40
        for kind, lab in items:
            if kind == "zone":
                self.front.append(f'<rect x="{x}" y="{y - 11}" width="26" height="16" rx="4" fill="none" stroke="#1F3A5F" stroke-width="2"/>')
            elif kind == "arrow":
                self.front.append(f'<path d="M{x},{y - 3} L{x + 26},{y - 3}" stroke="{LINE}" stroke-width="1.6" marker-end="url(#ah)"/>')
            elif kind == "dashed":
                self.front.append(f'<path d="M{x},{y - 3} L{x + 26},{y - 3}" stroke="{LINE}" stroke-width="1.6" stroke-dasharray="6 4" marker-end="url(#ah)"/>')
            else:
                fill, stroke, *_rest = STYLE[kind]
                sw, dash = STYLE[kind][4], STYLE[kind][5]
                d = f' stroke-dasharray="{dash}"' if dash else ""
                self.front.append(f'<rect x="{x}" y="{y - 11}" width="26" height="16" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="{min(sw, 2)}"{d}/>')
            self.front.append(f'<text x="{x + 34}" y="{y + 2}" font-size="12.5" fill="{INK}">{escape(lab)}</text>')
            x += 34 + len(lab) * 6.6 + 30
        if note:
            self.text(40, y + 28, note, 12.5)

    def svg(self) -> str:
        defs = ('<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
                f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>')
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="{FONT}" role="img">\n{defs}\n<rect width="{self.w}" height="{self.h}" fill="{BG}"/>\n'
                + "\n".join(self.back + self.mid + self.front) + "\n</svg>\n")

    # helpers: box edge points
    def L(self, k: str, f: float = 0.5) -> tuple[float, float]:
        x, y, w, h = self.boxes[k]; return (x, y + h * f)

    def R(self, k: str, f: float = 0.5) -> tuple[float, float]:
        x, y, w, h = self.boxes[k]; return (x + w, y + h * f)

    def T(self, k: str, f: float = 0.5) -> tuple[float, float]:
        x, y, w, h = self.boxes[k]; return (x + w * f, y)

    def B(self, k: str, f: float = 0.5) -> tuple[float, float]:
        x, y, w, h = self.boxes[k]; return (x + w * f, y + h)


# ---- 1. System context ---------------------------------------------------------------------------------------------
def system_context() -> Diagram:
    d = Diagram(1620, 790, "IntentSeal in context",
                "Between an AI agent and everything it reads and does: content is inspected before the model sees it; "
                "tool calls are checked before they run; every decision is recorded.")
    d.zone(40, 220, 270, 440, "Untrusted content", "untrusted")
    for i, (t, s) in enumerate([("Web pages", ""), ("Files and documents", "PDF · Word · Markdown · code"),
                                ("Images", "text read by OCR"), ("Email", ""), ("APIs and databases", ""),
                                ("Retrieved passages", "RAG")]):
        d.box(f"u{i}", 62, 256 + i * 66, 226, 52, t, s, "untrusted")
    d.zone(350, 90, 300, 570, "Your environment", "plain")
    d.box("user", 410, 120, 130, 50, "User", "", "external")
    d.box("agent", 380, 300, 240, 90, "Your AI agent", ["any framework or language"], "external")
    d.box("tools", 380, 480, 240, 70, "Tools and side effects", "send · write · fetch · query", "external")
    d.zone(740, 220, 520, 440, "IntentSeal", "seal")
    d.box("inspect", 770, 290, 240, 90, "Inspect content", ["extract · decode · detect", "quarantine or hold"], "enforce")
    d.box("check", 770, 470, 240, 90, "Check actions", ["intent contract · allow-lists", "pinned fields · secret scan"], "enforce")
    d.box("log", 1060, 382, 170, 96, "Decision log", "rule · evidence · replay", "store")
    d.zone(1300, 220, 280, 440, "Security operations", "plain")
    d.box("console", 1325, 290, 230, 70, "Console", "replay · approvals · review", "external")
    d.box("siem", 1325, 480, 230, 70, "SIEM", "JSON Lines · CEF", "external")
    d.zone(1300, 90, 280, 100, "External service", "external")
    d.box("model", 1325, 116, 230, 56, "Model provider", "OpenAI · Anthropic · Gemini · …", "external")

    d.arrow([d.B("user"), (475, 300)], "task", dx=10, dy=4, anchor="start")
    d.arrow([(310, 345), d.L("agent")], "read", dy=-8)
    d.arrow([d.R("agent", 0.22), (770, 300 + 90 * 0.22 + 0)], "what it read", dy=-8)
    d.arrow([(770, 300 + 90 * 0.6), d.R("agent", 0.6)], "cleaned content", dy=-8)
    d.arrow([d.R("agent", 0.92), (690, 300 + 90 * 0.92), (690, 500), (770, 500)], "proposed tool call", at=1, dx=-8, dy=4, anchor="end")
    d.arrow([(770, 535), d.R("tools", 0.79)], "allowed calls only", dy=18)
    d.arrow([d.T("agent", 0.9), (596, 144), (1325, 144)], "model calls: through the IntentSeal proxy, or direct with the SDK / REST API", at=1, dx=40, dy=-8)
    d.arrow([d.R("inspect"), (1035, 335), (1035, 405), (1060, 405)])
    d.arrow([d.R("check"), (1035, 515), (1035, 455), (1060, 455)])
    d.arrow([d.R("log", 0.35), (1275, 382 + 96 * 0.35), (1275, 325), (1325, 325)])
    d.arrow([d.R("log", 0.65), (1275, 382 + 96 * 0.65), (1275, 515), (1325, 515)])
    d.legend(712, [("untrusted", "Untrusted input"), ("external", "Your systems and services"),
                   ("enforce", "IntentSeal enforcement point"), ("store", "Record"), ("zone", "Trust boundary")],
             "The LLM proxy sees what passes through model calls; the SDK and REST API check what the application routes "
             "through them. See docs/diagrams/INVENTORY.md.")
    return d


# ---- 2. Component architecture --------------------------------------------------------------------------------------
def components() -> Diagram:
    d = Diagram(1620, 1090, "Component architecture",
                "Every integration reaches one core engine; the AI models advise, the deterministic policy decides.")
    d.zone(40, 88, 1540, 112, "Agents and applications (unchanged code)", "plain")
    cl = [("oa", 60, "OpenAI-compatible agent", "base URL changed"), ("an", 290, "Anthropic SDK agent", "base URL changed"),
          ("ge", 520, "Gemini agent", "Google Gen AI SDK"), ("any", 790, "Any language", "HTTP calls"),
          ("py", 1090, "Python application", "Guard · @guard.tool()"), ("lc", 1340, "LangChain / LangGraph", "guard.protect_tools()")]
    for k, x, t, s in cl:
        d.box(k, x, 120, 210 if k not in ("py", "lc") else 220, 62, t, s, "external")
    d.zone(40, 230, 1000, 152, "Gateway · services/gateway", "seal", at="bottom")
    d.box("proxy", 60, 266, 680, 84, "LLM proxy", ["/proxy/<agent>/v1 · /anthropic/v1/messages · /gemini/v1beta",
                                                   "user messages and tool results inspected · returned tool calls and answers checked"], "enforce")
    d.box("rest", 770, 266, 250, 84, "REST API", ["/v1/inspect · /v1/actions/check", "/v1/outputs/check · /v1/sessions"], "enforce")
    d.zone(1070, 230, 510, 152, "Python SDK · packages/sdk", "seal", at="bottom")
    d.box("guard", 1090, 266, 470, 84, "Guard", ["embedded engine in-process, or", "remote client of the REST API"], "trusted")
    for k in ("oa", "an", "ge"):
        x, y, w, h = d.boxes[k]
        d.arrow([(x + w / 2, y + h), (x + w / 2, 266)])
    d.arrow([d.B("any"), (895, 266)])
    d.arrow([d.B("py"), (1200, 266)])
    d.arrow([d.B("lc"), (1450, 266)])
    d.arrow([d.L("guard"), d.R("rest")], "remote mode", dy=-8)

    d.zone(40, 410, 1540, 432, "Core engine · packages/core/intentseal_core", "seal", at="bottom")
    d.box("engine", 60, 446, 1500, 44, "Engine: inspect() · check_action() · check_output() · sessions", "", "trusted")
    d.arrow([d.B("proxy"), (400, 446)])
    d.arrow([d.B("rest"), (895, 446)])
    d.arrow([d.B("guard"), (1325, 446)], "embedded", dx=10, dy=4, anchor="start")
    d.text(60, 524, "CONTENT", 11, "#1F3A5F", weight=700)
    lane = [("ex", 60, 200, "Extract", "text · PDF · Word · OCR", "trusted"),
            ("nd", 280, 200, "Normalise, decode", "look-alikes · base64 · tags", "trusted"),
            ("t0", 500, 210, "Tier 0 rules", "structure · attack memory", "trusted"),
            ("t1", 730, 200, "Tier 1 classifier", "DeBERTa-v3, local", "ai"),
            ("t2", 950, 200, "Tier 2 judge", "intent vs the task", "ai"),
            ("pd", 1170, 390, "Policy decision", "ALLOW · NEUTRALISE · ESCALATE · BLOCK", "enforce")]
    for k, x, w, t, s, kind in lane:
        d.box(k, x, 536, w, 70, t, s, kind, tag="AI · ADVISES" if kind == "ai" else "")
    for a, b in zip(lane, lane[1:]):
        d.arrow([d.R(a[0]), d.L(b[0])])
    d.text(60, 640, "ACTIONS AND ANSWERS", 11, "#1F3A5F", weight=700)
    d.box("ct", 60, 652, 300, 70, "Intent contract", "from the user's words only", "trusted")
    d.box("ag", 390, 652, 500, 70, "Action guard",
          ["allow-lists · pinned fields · outbound scan", "provenance · data flow · session risk · contract"], "enforce")
    d.box("ac", 920, 652, 190, 70, "Answer check", "secrets redacted or withheld", "enforce", size=14)
    d.box("ss", 1190, 652, 370, 70, "Sessions", "risk · contract · data-flow origins", "trusted")
    d.arrow([d.R("ct"), d.L("ag")])
    d.box("pol", 60, 752, 300, 56, "Policies", "policies/<agent>.yaml", "store")
    d.box("lg", 390, 752, 500, 56, "Decision logger", "events · findings · actions · contracts · receipts", "trusted")
    d.box("rt", 1000, 752, 200, 56, "LLM router", "provider failover", "trusted")
    d.arrow([d.B("t2", 0.9), (1130, 752)], "judge calls", at=0, dx=8, dy=63, anchor="start")

    d.zone(40, 866, 1180, 116, "Evidence", "plain")
    d.box("db", 330, 890, 260, 70, "Store", "SQLite or PostgreSQL", "store")
    d.box("rd", 640, 890, 560, 70, "Gateway readers",
          ["Console · Investigator agent · provenance chains", "approvals · metrics · SIEM export"], "trusted")
    d.arrow([d.B("lg", 0.39), (585, 890 + 9)])
    d.arrow([d.R("db"), d.L("rd")])
    d.zone(1260, 866, 320, 116, "External services", "external")
    d.box("mp", 1290, 900, 260, 62, "Model providers", "OpenAI · Anthropic · Gemini · Groq …", "external")
    d.arrow([d.R("rt"), (1250, 780), (1250, 925), (1290, 925)], "model calls", at=1, dx=8, dy=-40, anchor="start")
    d.arrow([d.L("proxy", 0.5), (24, 308), (24, 1010), (1420, 1010), (1420, 960)],
            "LLM proxy: forwards the checked model call to the agent's provider", at=2, dx=0, dy=-8)
    d.legend(1050 + 0, [("external", "Outside IntentSeal"), ("trusted", "IntentSeal component"), ("ai", "AI model (advises)"),
                        ("enforce", "Enforcement point"), ("store", "Store or configuration"), ("zone", "Trust boundary")])
    return d


# ---- 4. Security provenance ----------------------------------------------------------------------------------------
def provenance() -> Diagram:
    d = Diagram(1620, 900, "Security provenance: from untrusted content to an attempted action",
                "Built from the decision log, the intent contract and execution receipts, not from what a model says.")
    d.zone(40, 96, 980, 150, "What the agent read", "untrusted")
    d.box("src", 64, 136, 260, 84, "Untrusted source", ["email, web page, file, API, record", "logged as an event"], "untrusted")
    d.box("ins", 384, 136, 280, 84, "Inspection", ["evidence spans and signals", "content decision"], "trusted")
    d.box("rec", 724, 136, 270, 84, "Session record", ["data-flow fingerprints", "where each target first appeared"], "store")
    d.arrow([d.R("src"), d.L("ins")])
    d.arrow([d.R("ins"), d.L("rec")])
    d.zone(40, 290, 520, 150, "What the user asked for", "plain")
    d.box("task", 64, 330, 200, 84, "User's words", ["task and later turns", "never third-party text"], "external")
    d.box("ct", 320, 330, 220, 84, "Intent contract", ["versioned · hash-chained", "permit · prohibit · ask first"], "trusted")
    d.arrow([d.R("task"), d.L("ct")])
    d.box("call", 64, 520, 476, 76, "The agent's model proposes a tool call", "e.g. send_message(to = an address from the email)", "external")

    d.zone(620, 290, 440, 470, "Action checks · worst result wins", "seal", at="bottom")
    checks = [("Intent contract", "prohibited or not requested"), ("Tool allowed for this agent", ""),
              ("Pinned fields", "rewritten from trusted context"), ("Outbound secret scan", "also encoded"),
              ("Allow-lists", "recipients · domains · paths"), ("Provenance", "target only in untrusted content"),
              ("Data flow", "arguments copy flagged content"), ("Session risk", "after untrusted content")]
    for i, (t, s) in enumerate(checks):
        d.box(f"c{i}", 640, 306 + i * 52, 400, 44, t if not s else f"{t}: {s}", "", "trusted", size=13.5)
    d.arrow([d.B("rec", 0.5), (859, 290)], "proven links", dx=10, dy=0, anchor="start")
    d.arrow([d.R("ct", 0.2), (640, 330 + 84 * 0.2)], "clause", dy=-8)
    d.arrow([d.R("call"), (590, 558), (590, 506), (620, 506)])

    d.diamond("dec", 1150, 525, 60, "Decision")
    d.arrow([(1060, 525), d.L("dec")])
    d.zone(1250, 290, 340, 470, "Outcome", "plain")
    d.box("run", 1272, 330, 296, 96, "Executed", ["with the checked arguments", "application receipt: ran"], "allow")
    d.box("no", 1272, 477, 296, 96, "Not executed", ["call withheld · the model is told", "and continues another way"], "block")
    d.box("hold", 1272, 624, 296, 96, "Held for a reviewer", ["an approval lets this exact", "call run once; never a BLOCK"], "hold")
    d.arrow([d.T("dec"), (1150, 378), (1272, 378)], "ALLOW", at=1, dy=-8)
    d.arrow([d.R("dec"), (1272, 525)], "BLOCK", dy=-8)
    d.arrow([d.B("dec"), (1150, 672), (1272, 672)], "ESCALATE", at=1, dy=-8)

    d.box("log", 620, 800, 400, 64, "Decision log and receipts", "rule · reason · clause · evidence · receipt", "store")
    d.box("chain", 1110, 800, 470, 64, "Provenance chain in the Console",
          "source → evidence → call → rule and clause → outcome", "trusted")
    d.arrow([d.R("hold", 0.5), (1604, 672), (1604, 780), (820, 780), (820, 800)], head=True)
    d.arrow([d.R("no", 0.5), (1604, 525), (1604, 672)], head=False)
    d.arrow([d.R("run", 0.5), (1604, 378), (1604, 525)], head=False)
    d.arrow([d.R("log"), d.L("chain")])
    d.text(40, 838, "Proven link: the call's arguments copy the content's text, or its target", 12.5)
    d.text(40, 856, "first appeared there. Otherwise the chain shows earlier flagged content as", 12.5)
    d.text(40, 874, "context, not proof. Proxy agents send no receipts: the withheld call is the record.", 12.5)
    return d


# ---- 5. Evaluation architecture -------------------------------------------------------------------------------------
def evaluation() -> Diagram:
    d = Diagram(1620, 820, "Evaluation architecture",
                "Generated attacks, held-out benign sets, protected and unprotected runs on one engine fingerprint, "
                "deterministic scoring, generated reports.")
    d.zone(40, 96, 250, 330, "Generators", "untrusted")
    d.box("pf", 62, 136, 206, 66, "promptfoo", "red-team plugins", "untrusted")
    d.box("gk", 62, 222, 206, 66, "NVIDIA garak", "probe families", "untrusted")
    d.text(62, 320, "Attack text is never", 12.5)
    d.text(62, 338, "hand-written (D-005)", 12.5)
    d.zone(330, 96, 300, 330, "Corpora", "plain")
    d.box("att", 352, 136, 256, 84, "Attack suites", ["v3 · headline · v2e · broad · mt3", "out-of-distribution garak"], "untrusted")
    d.box("ben", 352, 250, 256, 84, "Benign sets", ["development hb3 · held-out ho1", "+ 20 utility tasks (benign.py)"], "external")
    d.arrow([d.R("pf"), (352, 169)])
    d.arrow([d.R("gk"), (310, 255), (310, 200), (352, 200)])
    d.box("del", 670, 136, 250, 84, "Delivery", ["each payload through 14 channels", "eval/promptfoo/build_suites.py"], "trusted")
    d.arrow([d.R("att"), d.L("del")])
    d.zone(960, 96, 290, 330, "Agent target · protection arm", "seal")
    arms = [("off", "off", "unprotected", "external"), ("on", "on", "full protection", "enforce"),
            ("act", "actions", "detectors off", "trusted"), ("det", "detect", "content checkpoint, no agent", "trusted")]
    for i, (k, t, s, kind) in enumerate(arms):
        d.box(k, 982, 132 + i * 70, 246, 58, t, s, kind)
    d.arrow([d.R("del"), (960, 178)])
    d.arrow([d.R("ben", 0.5), (940, 292), (940, 370), (960, 370)], "false-alarm runs", at=0, dx=0, dy=-8)
    d.box("ag", 1290, 136, 290, 110, "Reference agent", ["arms off · on · actions (detect: none)", "real model, real tool calls", "sandbox: canaries, outbox, records"], "external")
    d.box("sc", 1290, 300, 290, 110, "Deterministic scoring", ["external sends · canary leaks", "writes · fetches · record access", "engine fingerprint per result"], "trusted")
    d.arrow([(1250, 191), d.L("ag")])
    d.arrow([d.B("ag"), d.T("sc")])

    d.zone(40, 470, 1540, 180, "Analysis · eval/intentseal_eval", "seal", at="bottom")
    an = [("sum", "summary", "recall · FPR · attack success"), ("pair", "paired", "same attacks · repeats · 95% CI"),
          ("ce", "contract_eval", "detectors bypassed, worst case"), ("rt", "redteam", "cluster · mutate · repair gate"),
          ("gr", "grid", "types × input sources")]
    for i, (k, t, s) in enumerate(an):
        d.box(k, 62 + i * 302, 512, 276, 70, t, s, "trusted")
    d.arrow([d.B("sc"), (1435, 450), (190, 450), (190, 512)], "raw results", at=1, dy=-8)
    for k in ("pair", "ce", "rt", "gr"):
        x, y, w, h = d.boxes[k]
        d.arrow([(x + w / 2, 450), (x + w / 2, 512)], head=True)
    d.text(62, 612, "Promotion gate: a red-team repair goes to a reviewer only with ≥ 90% of variants caught and zero new false alarms; nothing deploys itself.", 12.5)

    d.zone(40, 690, 1100, 100, "Reports (generated, never hand-typed)", "plain")
    for i, (t, s) in enumerate([("EVALUATION.md", "detection, false alarms"), ("ASSURANCE.md", "when detection fails"),
                                ("COVERAGE.md", "type × source grid"), ("README · deck", "metrics from reports")]):
        d.box(f"r{i}", 62 + i * 268, 722, 248, 54, t, s, "store")
    d.box("ci", 1190, 704, 390, 72, "CI on every push", ["pytest: engine, gateway, SDK, storage", "lint · secret scan · fixtures rebuilt"], "trusted")
    d.arrow([(1100, 650), (1100, 690)], "", head=True)
    return d


# ---- 3. Runtime sequence -------------------------------------------------------------------------------------------
def runtime_sequence() -> Diagram:
    d = Diagram(1560, 1290, "Runtime sequence: a poisoned email, then a hijacked action",
                "One session through the SDK or REST API. Through the LLM proxy, the inspection (6) and the action check (13) "
                "happen inside the proxy, as the tool result and the tool call pass through it.")
    lanes = {"U": (130, "User", "external"), "A": (360, "Agent", "external"), "E": (680, "IntentSeal engine", "enforce"),
             "J": (980, "AI judge (advises)", "ai"), "T": (1210, "Tool", "external"), "L": (1420, "Decision log", "store")}
    top, bottom = 96, 1230
    for k, (x, lab, kind) in lanes.items():
        d.back.append(f'<path d="M{x},{top + 46} L{x},{bottom}" stroke="#B6BDC8" stroke-width="1.4" stroke-dasharray="4 4"/>')
        d.box("h" + k, x - 95, top, 190, 46, lab, "", kind if kind != "store" else "trusted")
    y = [top + 86]

    def band(label: str, fill: str, stroke: str):
        """A phase band; returns a function that closes it at the current position (height fits its content)."""
        start = y[0] - 22
        d.text(266, start + 18, label.upper(), 11.5, stroke, weight=700)
        y[0] += 36

        def close() -> None:
            d.back.insert(0, f'<rect x="250" y="{start}" width="1260" height="{y[0] - start - 14}" rx="10" fill="{fill}" '
                             f'stroke="{stroke}" stroke-width="1.2"/>')
            y[0] += 24
        return close

    def msg(n: int, a: str, b: str, label: str, reply: bool = False, step: float = 46) -> None:
        xa, xb = lanes[a][0], lanes[b][0]
        d.arrow([(xa, y[0]), (xb, y[0])], dashed=reply)
        lx = (xa + xb) / 2
        text = f"{n}  {label}"
        wid = len(text) * 6.5 + 12
        d.front.append(f'<rect x="{lx - wid / 2}" y="{y[0] - 21}" width="{wid}" height="17" rx="3" fill="{BG}"/>')
        d.front.append(f'<text x="{lx}" y="{y[0] - 8}" font-size="12.5" fill="{INK}" text-anchor="middle">'
                       f'<tspan font-weight="700" fill="#1F3A5F">{n}</tspan>  {escape(label)}</text>')
        y[0] += step

    def work(n: int, lane: str, title: str, sub: str, kind: str = "trusted", w: float = 420) -> None:
        x = lanes[lane][0]
        d.box(f"w{n}", x - w / 2, y[0] - 16, w, 50, f"{n}  {title}", sub, kind, size=13.5)
        y[0] += 64

    msg(1, "U", "A", "task: \"summarise the partner email; do not reply to anyone\"")
    msg(2, "A", "E", "start session (task)")
    msg(3, "E", "L", "intent contract v1: permit read, prohibit send")
    close = band("The agent reads untrusted content", "#FFF7F0", "#C2410C")
    msg(4, "A", "T", "read_email()")
    msg(5, "T", "A", "raw email (third-party content)", reply=True)
    msg(6, "A", "E", "inspect(content, source = email)", step=40)
    work(7, "E", "Extract, normalise, decode", "Tier 0 rules and attack memory · Tier 1 classifier score")
    msg(8, "E", "J", "assess flagged chunks against the task")
    msg(9, "J", "E", "risk · attack types · evidence spans", reply=True, step=40)
    work(10, "E", "Deterministic policy decision", "ALLOW · NEUTRALISE · ESCALATE · BLOCK", "enforce")
    msg(11, "E", "L", "content decision · findings · data-flow fingerprint")
    msg(12, "E", "A", "cleaned content, or a held notice", reply=True)
    close()
    close = band("The model proposes an action", "#EEF2F8", "#1F3A5F")
    msg(13, "A", "E", "check_action(send_message, to = partner@vendor.example)", step=40)
    work(14, "E", "Action checks: worst result wins", "contract · allow-lists · pinned · secret scan · provenance · data flow · risk",
         "enforce", w=520)
    msg(15, "E", "L", "action decision · contract clause · links to its source", step=44)
    fy = y[0] - 14
    d.front.append(f'<rect x="280" y="{fy}" width="44" height="20" rx="4" fill="#1F3A5F"/><text x="302" y="{fy + 14}" font-size="11.5" font-weight="700" fill="#FFFFFF" text-anchor="middle">alt</text>')
    d.text(334, fy + 15, "[ALLOW]", 12.5, "#2F6B4F", weight=700)
    y[0] += 34
    msg(16, "E", "A", "allowed, with the checked arguments", reply=True)
    msg(17, "A", "T", "run the tool")
    msg(18, "A", "E", "execution receipt: ran (stored in the log)", step=40)
    d.back.append(f'<path d="M280,{y[0] - 8} L1480,{y[0] - 8}" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="5 4"/>')
    d.text(334, y[0] + 8, "[BLOCK or ESCALATE]", 12.5, "#9B1C1C", weight=700)
    y[0] += 34
    msg(19, "E", "A", "notice: not performed, with the reason", reply=True, step=30)
    d.box("never", 1050, y[0] - 14, 320, 50, "The tool is never called", "an ESCALATE waits for a reviewer's approval", "block", size=13.5)
    y[0] += 58
    d.back.append(f'<rect x="280" y="{fy}" width="1200" height="{y[0] - fy - 10}" rx="6" fill="none" stroke="#6B7280" stroke-width="1.2" stroke-dasharray="5 4"/>')
    y[0] += 20
    close()
    y[0] += 10
    msg(20, "A", "E", "check_output(answer)")
    msg(21, "E", "A", "answer, secrets redacted or withheld", reply=True)
    msg(22, "A", "U", "answer", reply=True)
    d.h = int(y[0] + 50)
    for i, line in enumerate(d.back):   # lifelines end at the last message
        if 'stroke="#B6BDC8"' in line:
            d.back[i] = line.replace(f"L{line.split(' L')[1].split(',')[0]},{bottom}", f"L{line.split(' L')[1].split(',')[0]},{y[0] - 30}")
    d.legend(y[0] + 10, [("external", "Outside IntentSeal"), ("enforce", "Enforcement point"), ("ai", "AI model (advises)"),
                    ("trusted", "IntentSeal processing"), ("dashed", "Reply")])
    return d


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in (("system-context", system_context), ("components", components), ("runtime-sequence", runtime_sequence),
                     ("provenance", provenance), ("evaluation", evaluation)):
        (OUT / f"{name}.svg").write_text(fn().svg(), encoding="utf-8")
        print("wrote", OUT / f"{name}.svg")


if __name__ == "__main__":
    main()
