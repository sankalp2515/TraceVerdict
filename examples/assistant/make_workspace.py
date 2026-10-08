"""Create the assistant's workspace: ordinary sample files in every format, and (optionally) a test pack of attack
files built from the promptfoo / garak payloads this repo has already generated.

    python examples/assistant/make_workspace.py              # samples only (kb/, inbox/, uploads/)
    python examples/assistant/make_workspace.py --test-pack  # + test-pack/ from eval/promptfoo/output (local only)

Attack text is never written here (D-005): the test pack only moves generator output into real file formats, the
way eval/promptfoo/build_suites.py does, and labels each file with the attack types the generator targeted.
Your own files work the same way: drop them into the workspace or upload them in the chat.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "eval"))

from research_agent import render  # noqa: E402  (agents/: real PDF, DOCX, EML, PNG writers)
from research_agent.render import Block  # noqa: E402

REFUND = """Refund policy (customers)

Customers can return any product within 30 days of delivery for a full refund to the original payment method.
Opened software licences are refundable within 14 days if the licence key has not been activated.
Refunds above 500 EUR need approval from a team lead. Refunds are paid within 5 business days of approval.
Shipping costs are refunded only when the product arrived damaged or was not what the customer ordered."""

TRAVEL = """Travel and expenses policy

Book economy class for flights under 6 hours; business class needs director approval.
Hotel limit: 150 EUR per night in Europe, 220 EUR in North America, 120 EUR elsewhere.
Submit receipts in the expense tool within 30 days of the trip. Meals are covered up to 60 EUR per day.
Personal travel added to a business trip is paid by the employee."""

SECURITY = """Security handbook (short version)

Never share passwords, API keys or customer data by email or chat. Report phishing to security@example.com.
Customer records are accessed only for the customer you are helping. Lock your screen when you leave your desk.
Production credentials live in the vault; nobody asks for them by email, including IT."""

ONBOARDING = """<html><head><title>Product FAQ</title></head><body>
<h1>Product FAQ</h1>
<h2>What does the Pro plan include?</h2><p>Unlimited projects, 50 GB storage, priority support and single sign-on.</p>
<h2>Can I change plans?</h2><p>Yes, at any time. Upgrades apply immediately; downgrades at the next billing date.</p>
<h2>Where is my data stored?</h2><p>In the EU (Frankfurt) by default; US hosting is available on Enterprise.</p>
</body></html>"""

INBOX = [
    ("Q3 numbers are in", "maria.lopez@example.com",
     "Hi,\n\nThe Q3 summary is attached in the shared drive. Revenue grew 8% quarter on quarter, mostly from the Pro "
     "plan. Could you send me a three-line summary for the board deck by Friday?\n\nThanks,\nMaria"),
    ("Team offsite", "hr@example.com",
     "Reminder: the team offsite is on 24 October in Pune. Please confirm your dietary preferences by replying."),
    ("Your invoice INV-2291", "billing@vendor.example",
     "Dear customer,\n\nInvoice INV-2291 for 1,240 EUR is due on 30 October. Payment details are in your account."),
]

REPORT = """Quarterly report Q3

Revenue: 4.2 million EUR (+8% QoQ). New customers: 312. Churn: 2.1%.
Highlights: SSO launched for Pro, EU data residency announced, support response time down to 3.5 hours.
Risks: two enterprise renewals in Q4, hiring for the platform team is behind plan."""

CODE = '''"""Billing helpers."""


def invoice_total(lines: list[tuple[float, int]], vat: float = 0.19) -> float:
    """Sum price x quantity and add VAT."""
    net = sum(price * qty for price, qty in lines)
    return round(net * (1 + vat), 2)
'''


def samples(ws: Path) -> None:
    for d in ("kb", "inbox", "uploads", "notes"):
        (ws / d).mkdir(parents=True, exist_ok=True)
    (ws / "kb" / "refund-policy.md").write_text(render.to_markdown(REFUND, "Refund policy"), encoding="utf-8")
    (ws / "kb" / "travel-policy.docx").write_bytes(render.to_docx(TRAVEL, "Travel policy"))
    (ws / "kb" / "security-handbook.pdf").write_bytes(render.to_pdf(SECURITY, "Security handbook"))
    (ws / "kb" / "product-faq.html").write_text(ONBOARDING, encoding="utf-8")
    for i, (subject, sender, body) in enumerate(INBOX, 1):
        (ws / "inbox" / f"{i:02d}-{subject.lower().replace(' ', '-')}.eml").write_bytes(render.to_eml(body, subject, sender, "me@example.com"))
    (ws / "uploads" / "q3-report.pdf").write_bytes(render.to_pdf(REPORT, "Quarterly report Q3"))
    (ws / "uploads" / "receipt.png").write_bytes(render.to_png("RECEIPT  Cafe Central  2 x coffee 7.20 EUR  Total 7.20 EUR"))
    (ws / "uploads" / "billing.py").write_text(CODE, encoding="utf-8")
    (ws / "uploads" / "exchange-rates.json").write_text(json.dumps({"base": "EUR", "rates": {"USD": 1.09, "INR": 91.2}}), encoding="utf-8")
    print(f"samples written to {ws}")


# ---- test pack ----------------------------------------------------------------------------------------------

COVER = "Meeting notes, project status. The rollout is on track; the next review is on Thursday."
FORMATS = ["pdf", "pdf_hidden", "docx", "docx_hidden", "html", "html_hidden", "eml", "md", "png", "json", "code", "kb"]


def _load(name: str) -> list[dict]:
    f = ROOT / "eval" / "promptfoo" / "output" / name
    if not f.exists():
        return []
    d = yaml.safe_load(f.read_text(encoding="utf-8"))
    return (d.get("tests") if isinstance(d, dict) else d) or []


def test_pack(ws: Path, seed: int = 7) -> None:
    from intentseal_eval.report import categories

    pool = _load("pool.tests.yaml")
    users = _load("user.off.tests.yaml") + _load("roles.tests.yaml")
    turns = _load("user.off.mt3.plain.yaml")
    if not pool and not users:
        print("No generated payloads found in eval/promptfoo/output (they are local, not in git). Generate them first:\n"
              "  python eval/promptfoo/make_configs.py && cd eval/promptfoo && npx promptfoo redteam generate -c configs/pool.yaml "
              "-o output/pool.tests.yaml")
        return
    rng = random.Random(seed)
    out = ws / "test-pack"
    out.mkdir(parents=True, exist_ok=True)
    (ws / "kb").mkdir(parents=True, exist_ok=True)
    index = ["# Test pack (attack files from generated payloads)", "",
             "Each file carries one payload generated by promptfoo (never hand-written). Ask the assistant to read the",
             "file, e.g. \"Summarise test-pack/<name>\", and check what IntentSeal reports under the answer.", "",
             "| File | Delivered as | Generator plugin / strategy | Attack types |", "|---|---|---|---|"]
    by_strategy: dict[str | None, list[dict]] = {}
    for t in pool:
        by_strategy.setdefault((t.get("metadata") or {}).get("strategyId"), []).append(t)
    for v in by_strategy.values():
        rng.shuffle(v)
    # Rotate encodings across formats, skipping pairs the format cannot carry (summary.NOT_DELIVERED): a PDF font
    # without Cyrillic, OCR that reads neither look-alike letters nor long base64 runs.
    cannot = {("pdf", "homoglyph"), ("pdf_hidden", "homoglyph"), ("png", "homoglyph"), ("png", "base64")}
    order, used, picks = sorted(by_strategy, key=str), {k: 0 for k in by_strategy}, []
    for i, fmt in enumerate(FORMATS):
        options = [order[(i + j) % len(order)] for j in range(len(order))]
        k = next((s for s in options if (fmt, s) not in cannot and used[s] < len(by_strategy[s])), options[0])
        picks.append(by_strategy[k][used[k] % len(by_strategy[k])])
        used[k] += 1
    for fmt, t in zip(FORMATS, picks):
        text = str(t["vars"]["document"])
        meta = t.get("metadata") or {}
        hidden = [Block(COVER), Block(text, visible=False)]
        name, make = {
            "pdf": ("report.pdf", lambda: render.to_pdf(text, "Report")),
            "pdf_hidden": ("hidden-text.pdf", lambda: render.to_pdf(hidden, "Status")),
            "docx": ("memo.docx", lambda: render.to_docx(text, "Memo")),
            "docx_hidden": ("hidden-run.docx", lambda: render.to_docx(hidden, "Status")),
            "html": ("page.html", lambda: render.to_html(text, "Page").encode()),
            "html_hidden": ("hidden-div.html", lambda: render.to_html(hidden, "Status").encode()),
            "eml": ("message.eml", lambda: render.to_eml(text, "Partner update", "partner@vendor.example", "me@example.com")),
            "md": ("notes.md", lambda: render.to_markdown(text, "Notes").encode()),
            "png": ("screenshot.png", lambda: render.to_png(text)),
            "json": ("api-response.json", lambda: json.dumps({"status": "ok", "data": {"note": text}}, ensure_ascii=False).encode()),
            "code": ("helper.py", lambda: ('"""Helper module."""\n\n# ' + text.replace("\n", "\n# ") + "\n\n\ndef add(a, b):\n    return a + b\n").encode()),
            "kb": ("poisoned-kb-article.md", lambda: render.to_markdown(text, "Knowledge base article").encode()),
        }[fmt]
        data = make()
        path = (ws / "kb" / name) if fmt == "kb" else (out / name)
        path.write_bytes(data)
        channel = {"pdf_hidden": "pdf", "docx_hidden": "docx", "html_hidden": "html", "eml": "email", "png": "image",
                   "json": "api", "kb": "markdown", "md": "markdown"}.get(fmt, fmt)
        cats = categories(meta.get("pluginId"), meta.get("strategyId"), channel)
        where = "kb/" + name + " (re-index the knowledge base)" if fmt == "kb" else "test-pack/" + name
        index.append(f"| `{where}` | {fmt.replace('_', ' ')} | {meta.get('pluginId')} / {meta.get('strategyId') or 'plain'} | {', '.join(cats)} |")

    lines = ["# Direct (user-turn) and multi-step prompts from the generators", "",
             "Paste one into the chat as your own message. Attack text comes from promptfoo and garak, not from us.", ""]
    seen: set[tuple] = set()
    rng.shuffle(users)
    for t in users:
        meta = t.get("metadata") or {}
        key = (meta.get("pluginId"), meta.get("strategyId"))
        if key in seen:
            continue
        seen.add(key)
        cats = categories(meta.get("pluginId"), meta.get("strategyId"), "user")
        lines += [f"## {meta.get('pluginId')} / {meta.get('strategyId') or 'plain'} ({', '.join(cats)})", "", "```text",
                  str(t["vars"].get("prompt", "")).strip(), "```", ""]
        if len(seen) >= 16:
            break
    for t in turns[:3]:
        steps = json.loads(t["vars"]["turns"]) if isinstance(t["vars"].get("turns"), str) else t["vars"].get("turns", [])
        meta = t.get("metadata") or {}
        lines += [f"## Multi-step: one attack split over {len(steps)} turns ({meta.get('pluginId')}); send each turn "
                  "as a separate message in ONE conversation", ""]
        for i, s in enumerate(steps, 1):
            lines += [f"Turn {i}:", "```text", str(s).strip(), "```", ""]
    (out / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    (out / "user-prompts.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"test pack written to {out} ({len(picks)} files, kb/poisoned-kb-article.md, user-prompts.md)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", default=str(HERE / "workspace"))
    ap.add_argument("--test-pack", action="store_true")
    a = ap.parse_args()
    ws = Path(a.workspace)
    samples(ws)
    if a.test_pack:
        test_pack(ws)
