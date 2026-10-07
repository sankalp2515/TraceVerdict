"""CORE-6 Session state: accumulated risk (with decay) and simple provenance.

Provenance: entities (email addresses, URLs/domains, record IDs) that appeared in untrusted content but
not in the user's own messages or trusted context. A high-risk action whose target comes only from
untrusted content is a strong sign the action was steered by that content.
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

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
        out.add(domain_of(u))
    for r in _RECORD_ID.findall(text or ""):
        out.add(r.upper())
    return out


def domain_of(url_or_email: str) -> str:
    s = url_or_email.lower().strip()
    if "@" in s and "://" not in s:
        return s.rsplit("@", 1)[-1]
    s = re.sub(r"^[a-z]+://", "", s)
    return s.split("/", 1)[0].split("?", 1)[0].split(":", 1)[0]


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
    created_at: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if self.user_ref:
            self.user_ref = hashlib.sha256(self.user_ref.encode()).hexdigest()[:16]
        self.note_trusted(self.task)
        for v in self.trusted.values():
            self.note_trusted(str(v))

    def note_trusted(self, text: str) -> None:
        self.trusted_entities |= entities(text)

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
    """In-process session registry (the Gateway API persists sessions through the logger)."""

    def __init__(self) -> None:
        self._s: dict[str, Session] = {}

    def create(self, agent_id: str, **kw: Any) -> Session:
        s = Session(agent_id=agent_id, **kw)
        self._s[s.session_id] = s
        return s

    def get(self, session_id: str | None, agent_id: str) -> Session:
        if session_id and session_id in self._s:
            return self._s[session_id]
        s = Session(agent_id=agent_id, session_id=session_id or uuid.uuid4().hex[:16])
        self._s[s.session_id] = s
        return s
