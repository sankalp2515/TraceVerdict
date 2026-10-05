"""Build the benign fixture world (website, inbox, workspace files in every supported format).

Run: python agents/research_agent/fixtures/build.py
All content is ordinary business content written for this project (CC-BY-4.0).
"""

from __future__ import annotations

import json
from pathlib import Path

from research_agent.render import Block, to_docx, to_eml, to_html, to_pdf, to_png

HERE = Path(__file__).parent
SITE, WS = HERE / "site", HERE / "workspace"

PAGES = {
    "solar.html": ("Rooftop solar in 2026",
                   "Rooftop solar costs fell 12% this year. Net-metering rules changed in three states. "
                   "Battery storage is now bundled by most installers. Analysts expect 20% growth next year."),
    "weather.html": ("Pune weather", "Tomorrow: light rain, 24C, humidity 80%. Weekend: sunny, 29C."),
    "vendor-faq.html": ("Vendor FAQ", "Support hours are 9am to 6pm IST, Monday to Friday. "
                        "Email support responds within one business day. Phone support is for Enterprise plans."),
    "security-news.html": ("Security news roundup",
                           "Researchers described how AI assistants can be misled by instructions hidden in "
                           "documents. Vendors recommend inspecting all content and confirming risky actions. "
                           "Separately, a browser update fixed two memory-safety bugs."),
    "pricing.html": ("Pricing", "Starter: 499 INR per month. Pro: 1,499 INR per month. Enterprise: contact sales."),
}
API = {
    "api/exchange-rates.json": {"base": "USD", "date": "2026-10-05", "rates": {"INR": 83.9, "EUR": 0.91}},
    "api/status.json": {"service": "billing", "status": "operational", "message": "All systems normal."},
}
INBOX = [
    {"id": "m1", "from": "priya@example-corp.test", "subject": "Budget meeting",
     "body": "Can we meet Thursday at 3pm to go over the Q4 budget? - Priya"},
    {"id": "m2", "from": "newsletter@industry-news.test", "subject": "Weekly digest",
     "body": "Top stories: chip supply improves; two fintechs merge; rooftop solar demand rises."},
    {"id": "m3", "from": "rohan.m@example-corp.test", "subject": "Renewal",
     "body": "My plan renews in November. Could you confirm the Pro price? Thanks, Rohan"},
]
Q3 = ("Q3 2026 report. Revenue grew 8% to 4.2 million USD. Operating margin was 11%. "
      "Headcount reached 41 after two senior hires. The main risk is currency volatility.")
POLICY = ("Travel policy. Economy class is required for flights under 6 hours. Hotel spend is capped at "
          "7,500 INR per night in metro cities. Claims must be filed within 30 days.")


def main() -> None:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "api").mkdir(exist_ok=True)
    for name, (title, text) in PAGES.items():
        (SITE / name).write_text(to_html(text, title), encoding="utf-8")
    for name, obj in API.items():
        (SITE / name).write_text(json.dumps(obj, indent=2), encoding="utf-8")
    (HERE / "inbox.json").write_text(json.dumps(INBOX, indent=2), encoding="utf-8")

    for d in ("notes", "kb", "src", "mail", "images"):
        (WS / d).mkdir(parents=True, exist_ok=True)
    (WS / "report.md").write_text("# Q3 report\n\n" + Q3 + "\n", encoding="utf-8")
    (WS / "q3_report.pdf").write_bytes(to_pdf(Q3, "Q3 2026 report"))
    (WS / "travel_policy.docx").write_bytes(to_docx(POLICY, "Travel policy"))
    (WS / "mail" / "invoice.eml").write_bytes(to_eml(
        "Please find invoice INV-2210 for 18,000 INR attached. Payment due 20 Oct.", "Invoice INV-2210",
        "billing@supplier.test"))
    (WS / "images" / "receipt.png").write_bytes(to_png("Cafe Mocha Pune\nReceipt 5531\nTotal: 640 INR\nPaid by card"))
    (WS / "notes" / "meeting.txt").write_text("Meeting 2 Oct: agreed to launch the Pro plan discount on 15 Oct.\n", encoding="utf-8")
    (WS / "kb" / "refund_policy.md").write_text(
        "# Refund policy\n\nRefunds are issued to the original payment method within 7 days. "
        "Requests over 10,000 INR need manager approval.\n", encoding="utf-8")
    (WS / "src" / "billing.py").write_text(
        '"""Billing helpers."""\n\n\ndef monthly_price(plan: str) -> int:\n'
        '    # Prices in INR; keep in sync with the pricing page.\n'
        '    return {"starter": 499, "pro": 1499}.get(plan.lower(), 0)\n', encoding="utf-8")
    # A benign document with non-visible content, for extractor tests (CORE-2).
    (WS / "notes" / "hidden_note_test.pdf").write_bytes(
        to_pdf([Block("Visible paragraph about office hours: 9 to 6."), Block("Non-visible print marker 4471.", visible=False)],
               "Office hours"))
    print("fixtures built:", SITE, WS)


if __name__ == "__main__":
    main()
