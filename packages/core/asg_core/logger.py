"""CORE-10 Decision logger: every decision, with evidence, in the event store (PRD §10).

Privacy: content is stored as a hash plus a short redacted preview (or hash only when
ASG_STORE_PREVIEWS=0, e.g. public demo); user references are hashed; secrets, canaries and keys are
redacted before anything is written.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from typing import Any, Iterable

from .secrets import redact
from .store import Store
from .types import ActionResult, InspectResult

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY, agent_id TEXT, user_ref TEXT, task_preview TEXT, started_at REAL, risk REAL DEFAULT 0)""",
    """CREATE TABLE IF NOT EXISTS events (
        id TEXT PRIMARY KEY, session_id TEXT, agent_id TEXT, seq INTEGER, kind TEXT, source TEXT,
        content_hash TEXT, preview TEXT, created_at REAL)""",
    "CREATE INDEX IF NOT EXISTS ix_events_session ON events(session_id, seq)",
    """CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, span_start INTEGER, span_end INTEGER,
        span_preview TEXT, origin TEXT, signal TEXT, labels TEXT, score REAL, tier INTEGER)""",
    """CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, agent_id TEXT, session_id TEXT, decision TEXT,
        enforced TEXT, policy_rule TEXT, reason TEXT, labels TEXT, risk REAL, session_risk REAL, tier INTEGER,
        latency_ms REAL, degraded INTEGER, budget_degraded INTEGER, model TEXT, input_tokens INTEGER,
        est_cost REAL, created_at REAL)""",
    "CREATE INDEX IF NOT EXISTS ix_decisions_time ON decisions(created_at)",
    """CREATE TABLE IF NOT EXISTS actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT, tool TEXT, args_redacted TEXT,
        final_args_redacted TEXT, pinned_overrides TEXT)""",
]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:24]


class DecisionLogger:
    def __init__(self, store: Store, secrets_to_redact: Iterable[str] = ()) -> None:
        self.store = store
        self.store.ensure_schema(_SCHEMA)
        self.extra_secrets = [s for s in secrets_to_redact if s and len(s) >= 6]
        self.previews = os.environ.get("ASG_STORE_PREVIEWS", "1") != "0"
        self._seq: dict[str, int] = {}

    def add_secrets(self, values: Iterable[str]) -> None:
        self.extra_secrets += [v for v in values if v and len(v) >= 6]

    def scrub(self, text: str, limit: int = 160) -> str:
        if not self.previews:
            return ""
        t = redact(text or "")
        for s in self.extra_secrets:
            t = re.sub(re.escape(s), "[REDACTED]", t, flags=re.I)
        t = re.sub(r"\s+", " ", t).strip()
        return t[:limit] + ("…" if len(t) > limit else "")

    def scrub_obj(self, obj: Any) -> str:
        return self.scrub(json.dumps(obj, ensure_ascii=False, default=str), limit=600)

    # ---- writers ---------------------------------------------------------------------------
    def session(self, session_id: str, agent_id: str, user_ref: str | None, task: str) -> None:
        self.store.execute("INSERT OR IGNORE INTO sessions (id, agent_id, user_ref, task_preview, started_at) VALUES (?,?,?,?,?)",
                           (session_id, agent_id, user_ref, self.scrub(task), time.time()))

    def event(self, session_id: str, agent_id: str, kind: str, source: str, content: str = "") -> str:
        eid = uuid.uuid4().hex[:20]
        seq = self._seq.get(session_id, 0) + 1
        self._seq[session_id] = seq
        self.store.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?)",
                           (eid, session_id, agent_id, seq, kind, source, _hash(content) if content else None,
                            self.scrub(content), time.time()))
        return eid

    def inspection(self, session_id: str, agent_id: str, source: str, content: str, r: InspectResult,
                   model: str | None = None, input_tokens: int = 0, est_cost: float = 0.0) -> str:
        eid = self.event(session_id, agent_id, "content_in", source, content)
        for f in r.findings:
            self.store.execute(
                "INSERT INTO findings (event_id, span_start, span_end, span_preview, origin, signal, labels, score, tier) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (eid, f.span[0] if f.span else None, f.span[1] if f.span else None, self.scrub(f.preview, 120), f.origin,
                 f.signal, json.dumps(f.labels), f.score, f.tier))
        self._decision(eid, agent_id, session_id, r.decision.value, r.enforced.value, r.policy_rule, r.reason, r.labels,
                       r.risk, r.session_risk, r.tier, r.latency_ms, r.degraded, r.budget_degraded, model, input_tokens, est_cost)
        self.store.execute("UPDATE sessions SET risk = ? WHERE id = ?", (r.session_risk, session_id))
        return eid

    def action(self, session_id: str, agent_id: str, tool: str, args: dict[str, Any], r: ActionResult,
               session_risk: float) -> str:
        eid = self.event(session_id, agent_id, "action", f"tool:{tool}")
        self.store.execute("INSERT INTO actions (event_id, tool, args_redacted, final_args_redacted, pinned_overrides) VALUES (?,?,?,?,?)",
                           (eid, tool, self.scrub_obj(args), self.scrub_obj(r.final_args) if r.final_args else None,
                            self.scrub_obj(r.pinned_overrides) if r.pinned_overrides else None))
        self._decision(eid, agent_id, session_id, r.decision.value, r.enforced.value, r.policy_rule, r.reason, r.labels,
                       0.0, session_risk, 0, r.latency_ms, r.degraded, False, None, 0, 0.0)
        return eid

    def _decision(self, eid, agent_id, session_id, decision, enforced, rule, reason, labels, risk, session_risk, tier,
                  latency_ms, degraded, budget_degraded, model, input_tokens, est_cost) -> None:
        self.store.execute(
            "INSERT INTO decisions (event_id, agent_id, session_id, decision, enforced, policy_rule, reason, labels, risk, "
            "session_risk, tier, latency_ms, degraded, budget_degraded, model, input_tokens, est_cost, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (eid, agent_id, session_id, decision, enforced, rule, self.scrub(reason, 400), json.dumps(labels), risk,
             session_risk, tier, latency_ms, int(degraded), int(budget_degraded), model, input_tokens, est_cost, time.time()))

    # ---- readers (API / Console) ------------------------------------------------------------
    def session_events(self, session_id: str) -> list[dict[str, Any]]:
        rows = self.store.query(
            "SELECT e.*, d.decision, d.enforced, d.policy_rule, d.reason, d.labels, d.tier, d.latency_ms, d.degraded, "
            "d.session_risk FROM events e LEFT JOIN decisions d ON d.event_id = e.id WHERE e.session_id = ? ORDER BY e.seq",
            (session_id,))
        for r in rows:
            r["labels"] = json.loads(r["labels"]) if r.get("labels") else []
            r["findings"] = [dict(f, labels=json.loads(f["labels"] or "[]"))
                             for f in self.store.query("SELECT * FROM findings WHERE event_id = ?", (r["id"],))]
            act = self.store.query("SELECT tool, args_redacted, final_args_redacted, pinned_overrides FROM actions WHERE event_id = ?", (r["id"],))
            r["action"] = act[0] if act else None
        return rows

    def decisions(self, decision: str | None = None, label: str | None = None, agent: str | None = None,
                  since: float | None = None, limit: int = 200) -> list[dict[str, Any]]:
        q, p = "SELECT d.*, e.source, e.kind, e.preview FROM decisions d JOIN events e ON e.id = d.event_id WHERE 1=1", []
        if decision:
            q += " AND d.decision = ?"; p.append(decision)
        if agent:
            q += " AND d.agent_id = ?"; p.append(agent)
        if since:
            q += " AND d.created_at >= ?"; p.append(since)
        if label:
            q += " AND d.labels LIKE ?"; p.append(f'%"{label}"%')
        q += " ORDER BY d.created_at DESC LIMIT ?"; p.append(limit)
        rows = self.store.query(q, tuple(p))
        for r in rows:
            r["labels"] = json.loads(r["labels"] or "[]")
        return rows
