"""Sandboxed tools for the reference agent (REF-2). All side effects stay inside the World.

File reading mimics what a typical agent does (plain library extraction), so the unprotected
baseline sees documents the way real agents do.
"""

from __future__ import annotations

import email
import email.policy
import io
import json
from pathlib import Path
from typing import Any, Callable

from .world import World

READ_TOOLS = {"web_fetch", "read_file", "read_email", "query_db"}   # bring content in
WRITE_TOOLS = {"write_file", "send_message"}                       # act on the world

SCHEMAS: list[dict[str, Any]] = [
    {"type": "function", "function": {"name": n, "description": d, "parameters": {
        "type": "object", "properties": p, "required": r}}}
    for n, d, p, r in [
        ("web_fetch", "Fetch a web page or API URL and return its text.", {"url": {"type": "string"}}, ["url"]),
        ("read_file", "Read a file from the user's workspace (txt, md, html, pdf, docx, eml, json, code, images).",
         {"path": {"type": "string"}}, ["path"]),
        ("read_email", "List the user's recent emails with sender, subject and body.",
         {"limit": {"type": "integer"}}, []),
        ("query_db", "Look up a customer record by customer_id.", {"customer_id": {"type": "string"}}, ["customer_id"]),
        ("write_file", "Write a text file into the user's workspace.",
         {"path": {"type": "string"}, "text": {"type": "string"}}, ["path", "text"]),
        ("send_message", "Send an email message.",
         {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, ["to", "subject", "body"]),
    ]
]


def extract_file_naive(path: Path) -> str:
    """What a typical agent's loader returns (no inspection, no hidden-content awareness)."""
    suf = path.suffix.lower()
    data = path.read_bytes()
    if suf == ".pdf":
        from pypdf import PdfReader
        r = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in r.pages)
    if suf == ".docx":
        import docx
        d = docx.Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    if suf == ".eml":
        m = email.message_from_bytes(data, policy=email.policy.default)
        body = m.get_body(preferencelist=("plain", "html"))
        return f"From: {m['from']}\nSubject: {m['subject']}\n\n{body.get_content() if body else ''}"
    if suf in (".png", ".jpg", ".jpeg"):
        try:
            from rapidocr_onnxruntime import RapidOCR  # optional; images are text-only via OCR
            res, _ = RapidOCR()(data)
            return "\n".join(r[1] for r in (res or []))
        except ImportError:
            return "[image: no text extraction available]"
    return data.decode("utf-8", errors="replace")


class Toolbox:
    def __init__(self, world: World) -> None:
        self.world = world
        self._impl: dict[str, Callable[..., str]] = {
            "web_fetch": self.web_fetch, "read_file": self.read_file, "read_email": self.read_email,
            "query_db": self.query_db, "write_file": self.write_file, "send_message": self.send_message,
        }

    def run(self, name: str, args: dict[str, Any]) -> str:
        fn = self._impl.get(name)
        if fn is None:
            return f"error: unknown tool {name}"
        try:
            return fn(**{k: v for k, v in args.items() if k in fn.__code__.co_varnames})
        except TypeError as e:
            return f"error: bad arguments ({e})"

    def web_fetch(self, url: str) -> str:
        url = url.strip()
        if url.startswith("http://"):
            url = "https://" + url[7:]
        return self.world.pages.get(url) or self.world.pages.get(url.rstrip("/")) or "HTTP 404: page not found"

    def _safe_path(self, path: str) -> Path | None:
        p = (self.world.workspace / path.lstrip("/\\")).resolve()
        return p if str(p).startswith(str(self.world.workspace.resolve())) else None

    def read_file(self, path: str) -> str:
        p = self._safe_path(path)
        if p is None:
            return "error: path outside workspace"
        if not p.exists():
            return "error: file not found"
        return extract_file_naive(p)

    def read_email(self, limit: int = 10) -> str:
        return json.dumps(self.world.inbox[-int(limit or 10):], ensure_ascii=False)

    def query_db(self, customer_id: str) -> str:
        r = self.world.db.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id.strip(),)).fetchone()
        return json.dumps(dict(r)) if r else json.dumps({"error": "customer not found"})

    def write_file(self, path: str, text: str) -> str:
        p = self._safe_path(path)
        self.world.writes.append({"path": path, "text": text, "inside_sandbox": p is not None})
        if p is None:
            return "error: path outside workspace"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return "ok"

    def send_message(self, to: str, subject: str = "", body: str = "") -> str:
        msg = {"to": to, "subject": subject, "body": body}
        self.world.outbox.append(msg)
        with open(self.world.outbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(msg) + "\n")
        return "sent (sandbox outbox)"
