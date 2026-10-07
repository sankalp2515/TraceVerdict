"""CORE-6 Session state: accumulated risk (with decay) and simple provenance.

Provenance: entities (email addresses, URLs/domains, record IDs) that appeared in untrusted content but
not in the user's own messages or trusted context. A high-risk action whose target comes only from
untrusted content is a strong sign the action was steered by that content.
"""

from __future__ import annotations

import hashlib
import os
import re
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from .taint import TaintTracker

_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"https?://[^\s\"'<>)\]]+", re.I)
_DOMAIN = re.compile(r"\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b", re.I)
_RECORD_ID = re.compile(r"\b[A-Z]{1,4}-\d{3,}\b")


def entities(text: str) -> set[str]:
    """Normalised entities an action could target."""
    out: set[str] = set()
    for e in _EMAIL.findall(text or ""):
        out.add(e.lower())
    for u in _URL.findall(text or ""):
        out.add(u.lower().rstrip(".,;"))
        if d := domain_of(u):
            out.add(d)
    for r in _RECORD_ID.findall(text or ""):
        out.add(r.upper())
    return out


_HOST = re.compile(r"^[a-z0-9-]+(\.[a-z0-9-]+)*$")


def domain_of(url_or_email: str) -> str:
    """Host an HTTP client or mailer would actually use; "" when it is ambiguous.

    Parsed with the standard library, so a fragment, query, port or user part can never pose as the host
    (`https://evil.example#.allowed.test` is evil.example). Backslashes, whitespace and user parts are
    rejected outright: clients disagree on them."""
    s = url_or_email.lower().strip()
    if "@" in s and "://" not in s:
        return s.rsplit("@", 1)[-1].strip(" >")
    if "\\" in s or any(c.isspace() or ord(c) < 32 for c in s):
        return ""
    try:
        parts = urlsplit(s if "://" in s else "//" + s)
        host = parts.hostname or ""
    except ValueError:
        return ""
    if "@" in parts.netloc or not _HOST.match(host):
        return ""
    return host


@dataclass
class Session:
    agent_id: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    user_ref: str | None = None            # stored hashed
    task: str = ""
    trusted: dict[str, Any] = field(default_factory=dict)   # e.g. {"customer_id": "C-1042"}
    risk: float = 0.0
    turns: int = 0
    labels: set[str] = field(default_factory=set)
    trusted_entities: set[str] = field(default_factory=set)
    untrusted_entities: set[str] = field(default_factory=set)
    flagged_untrusted: bool = False        # any finding in untrusted content this session
    taint: TaintTracker = field(default_factory=TaintTracker)   # CORE-17 data-flow origins (fingerprints only)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.user_ref:
            self.user_ref = hashlib.sha256(self.user_ref.encode()).hexdigest()[:16]
        self.note_trusted(self.task)
        for v in self.trusted.values():
            self.note_trusted(str(v))

    def note_trusted(self, text: str) -> None:
        self.trusted_entities |= entities(text)
        self.taint.observe(text, "", "user", trusted=True, flagged=False)

    def note_untrusted(self, text: str) -> None:
        self.untrusted_entities |= entities(text) - self.trusted_entities

    def from_untrusted_only(self, value: str) -> bool:
        ents = entities(value) or {value.lower().strip()}
        return any(e in self.untrusted_entities and e not in self.trusted_entities for e in ents)

    def new_turn(self, decay: float) -> None:
        self.turns += 1
        self.risk = max(0.0, self.risk - decay)

    def add_risk(self, amount: float, labels: list[str] | None = None) -> None:
        self.risk += max(0.0, amount)
        self.labels |= set(labels or [])


class SessionStore:
    """In-process session registry (the Gateway API persists sessions through the logger).

    Bounded: the least recently used sessions are dropped beyond `max_sessions` (INTENTSEAL_MAX_SESSIONS,
    default 20000), so a stream of one-off session ids cannot grow memory without limit."""

    def __init__(self, max_sessions: int | None = None) -> None:
        self._s: OrderedDict[str, Session] = OrderedDict()
        self.max_sessions = max_sessions or int(os.environ.get("INTENTSEAL_MAX_SESSIONS") or "20000")

    def __contains__(self, session_id: object) -> bool:
        return session_id in self._s

    def __len__(self) -> int:
        return len(self._s)

    def _keep(self, s: Session) -> Session:
        self._s[s.session_id] = s
        self._s.move_to_end(s.session_id)
        while len(self._s) > self.max_sessions:
            self._s.popitem(last=False)
        return s

    def create(self, agent_id: str, **kw: Any) -> Session:
        if not kw.get("session_id"):
            kw.pop("session_id", None)
        return self._keep(Session(agent_id=agent_id, **kw))

    def get(self, session_id: str | None, agent_id: str) -> Session:
        if session_id and session_id in self._s:
            return self._keep(self._s[session_id])
        return self._keep(Session(agent_id=agent_id, session_id=session_id or uuid.uuid4().hex[:16]))
