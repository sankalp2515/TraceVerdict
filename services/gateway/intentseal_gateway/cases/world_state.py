"""World Model reference architecture: append history, canon, contexts and CAS writes.

Application-owned implementation, not a claimed Meterless SDK. Each commit atomically
replaces an aggregate containing its immutable append history and derived projections.
The operational Store remains independent of the governed Zetaris read path.
"""
from __future__ import annotations

import json
import time
from copy import deepcopy
from typing import Any

from intentseal_core.store import Store

from .models import canonical, digest
from .world_model import WorldModel, safe_namespace


class Conflict(ValueError):
    pass


TRANSITIONS = {
    "COLLECTING": {"EXPLAINING", "INCOMPLETE"},
    "EXPLAINING": {"CRITIQUING", "INCOMPLETE"},
    "CRITIQUING": {"COLLECTING", "PROPOSING", "INCONCLUSIVE", "INCOMPLETE"},
    "PROPOSING": {"VALIDATING", "INCOMPLETE"},
    "VALIDATING": {"AWAITING_REVIEW", "REJECTED", "INCOMPLETE"},
    "AWAITING_REVIEW": {"APPROVED", "STALE"},
    "APPROVED": {"STALE"},
    "REJECTED": set(), "INCONCLUSIVE": set(), "INCOMPLETE": set(), "STALE": set(),
}


class WorldState:
    def __init__(self, store: Store):
        self.store = store
        store.ensure_schema([
            "CREATE TABLE IF NOT EXISTS tv_worlds (id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, "
            "agent_id TEXT NOT NULL, version INTEGER NOT NULL, request_hash TEXT NOT NULL, body TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS tv_world_scope ON tv_worlds(tenant_id, agent_id)",
            "CREATE TABLE IF NOT EXISTS tv_world_history (case_id TEXT NOT NULL,version INTEGER NOT NULL,body TEXT NOT NULL,PRIMARY KEY(case_id,version))",
            "CREATE TABLE IF NOT EXISTS tv_job_index (job_id TEXT PRIMARY KEY,case_id TEXT NOT NULL,status TEXT NOT NULL,lease_until REAL NOT NULL)",
            "CREATE INDEX IF NOT EXISTS tv_job_status ON tv_job_index(status,lease_until,case_id)",
            "CREATE TABLE IF NOT EXISTS tv_object_index (object_id TEXT PRIMARY KEY,kind TEXT NOT NULL,case_id TEXT NOT NULL,tenant_id TEXT NOT NULL)",
            "CREATE INDEX IF NOT EXISTS tv_object_scope ON tv_object_index(tenant_id,kind,object_id)",
            "CREATE TABLE IF NOT EXISTS tv_scheduler (id INTEGER PRIMARY KEY,max_running INTEGER NOT NULL)",
        ])
        store.execute("INSERT INTO tv_scheduler VALUES(1,2) ON CONFLICT DO NOTHING")
        # One-time index backfill for worlds created by the earlier schema. A restart
        # can rebuild indexes without changing canonical case history.
        for row in store.query("SELECT body FROM tv_worlds WHERE id NOT IN (SELECT case_id FROM tv_object_index WHERE kind='case')"):
            with store.transaction():
                self._index(json.loads(row["body"]))

    def _index(self, body: dict) -> None:
        entries = [(body["case_id"], "case")]
        entries += [(c["candidate_id"], "repair") for c in body["candidates"]]
        entries += [(r["validation_id"], "validation") for r in body["validations"].values()]
        for oid, kind in entries:
            self.store.execute("INSERT INTO tv_object_index VALUES(?,?,?,?) ON CONFLICT(object_id) DO NOTHING",
                               (oid, kind, body["case_id"], body["tenant_id"]))
        for jid, job in body["jobs"].items():
            self.store.execute("INSERT INTO tv_job_index VALUES(?,?,?,?) ON CONFLICT(job_id) DO UPDATE SET status=excluded.status,lease_until=excluded.lease_until",
                               (jid, body["case_id"], job["status"], job["lease_until"]))

    def object_case(self, oid: str, kind: str, tenant: str | None) -> str | None:
        rows = self.store.query("SELECT case_id FROM tv_object_index WHERE object_id=? AND kind=?" +
                                (" AND tenant_id=?" if tenant is not None else ""),
                                (oid, kind, tenant) if tenant is not None else (oid, kind))
        return rows[0]["case_id"] if rows else None

    def create(self, case_id: str, tenant: str, agent: str, request_hash: str, initial: dict) -> dict:
        body = {**deepcopy(initial), "case_id": case_id, "tenant_id": tenant, "agent_id": agent,
                "schema_version": 2, "state_version": 0, "status": "COLLECTING", "observations": [],
                "entities": {}, "contexts": {}, "relationships": [], "jobs": {}, "claims": [],
                "candidates": [], "validations": {}, "approvals": [], "model_calls": [], "revisions": 0}
        body["contexts"] = {"case": {"case_id": case_id, "agent_id": agent, "tenant_id": tenant}}
        with self.store.transaction():
            self.store.execute("INSERT INTO tv_worlds VALUES (?,?,?,?,?,?) ON CONFLICT (id) DO NOTHING",
                               (case_id, tenant, agent, 0, request_hash, canonical(body)))
            self._index(body)
        row = self.store.query("SELECT request_hash FROM tv_worlds WHERE id=?", (case_id,))[0]
        if row["request_hash"] != request_hash:
            raise Conflict("idempotency key reused with different input")
        return self.load(case_id, tenant, agent)

    def load(self, case_id: str, tenant: str, agent: str | None = None) -> dict:
        rows = self.store.query("SELECT body FROM tv_worlds WHERE id=? AND tenant_id=?", (case_id, tenant))
        if not rows:
            raise KeyError("case not found")
        body = json.loads(rows[0]["body"])
        if agent is not None and body["agent_id"] != agent:
            raise KeyError("case not found")
        return body

    def commit(self, body: dict, expected_version: int, actor: str, event: str, next_status: str | None = None) -> dict:
        old = self.load(body["case_id"], body["tenant_id"], body["agent_id"])
        if old["state_version"] != expected_version:
            raise Conflict("stale world state")
        if next_status and next_status != old["status"] and next_status not in TRANSITIONS[old["status"]]:
            raise Conflict("invalid state transition")
        # Immutable intake anchors cannot be rewritten by agents or queued jobs.
        for name in ("snapshots", "base_policy_sha256", "fixture_id", "execution_mode", "session_ids"):
            if body.get(name) != old.get(name):
                raise Conflict("immutable case anchor changed")
        if body["observations"] != old["observations"]:
            raise Conflict("append history cannot be rewritten")
        if not set(old["jobs"]) <= set(body["jobs"]):
            raise Conflict("durable jobs cannot be removed")
        old_events = old.get("world_model", {}).get("events", [])
        if body.get("world_model", {}).get("events", [])[:len(old_events)] != old_events:
            raise Conflict("canonical world model history cannot be rewritten")
        for eid, record in old["entities"].items():
            proposed = body["entities"].get(eid, {})
            if {k: v for k, v in record.items() if k != "query_receipt"} != {
                    k: v for k, v in proposed.items() if k != "query_receipt"}:
                raise Conflict("immutable evidence changed")
        new = deepcopy(body)
        new["status"] = next_status or old["status"]
        new["state_version"] = expected_version + 1
        projection = deepcopy({k: v for k, v in new.items() if k != "observations"})
        observation = {"agent_id": actor, "run_id": body["case_id"], "event": event,
                       "version": new["state_version"], "at": time.time(),
                       "parent_sha256": digest(old["observations"]),
                       "projection_sha256": digest(projection), "projection": projection}
        compact = new.get("schema_version", 1) >= 2
        new["observations"].append({k: v for k, v in observation.items() if k != "projection"} if compact else observation)
        with self.store.transaction():
            if set(new["jobs"]) - set(old["jobs"]) or event == "job_claimed":
                suffix = " FOR UPDATE" if self.store.backend == "postgres" else ""
                scheduler = self.store.query("SELECT max_running FROM tv_scheduler WHERE id=1" + suffix)[0]
                if set(new["jobs"]) - set(old["jobs"]) and self.active_count() >= 32:
                    raise Conflict("worker backlog is full")
                if event == "job_claimed":
                    running = self.store.query("SELECT COUNT(*) AS n FROM tv_job_index WHERE status='running' AND lease_until>?", (time.time(),))[0]["n"]
                    if running >= scheduler["max_running"]:
                        raise Conflict("worker concurrency limit reached")
            rows = self.store.query("UPDATE tv_worlds SET version=?,body=? WHERE id=? AND tenant_id=? AND version=? RETURNING id",
                                    (new["state_version"], canonical(new), new["case_id"], new["tenant_id"], expected_version))
            if not rows:
                raise Conflict("concurrent world update")
            if compact:
                self.store.execute("INSERT INTO tv_world_history VALUES(?,?,?)", (new["case_id"], new["state_version"], canonical(observation)))
            self._index(new)
        return new

    def at_version(self, case_id: str, tenant: str, version: int) -> dict:
        body = self.load(case_id, tenant)
        history = (self.store.query("SELECT body FROM tv_world_history WHERE case_id=? AND version=?", (case_id, version))
                   if body.get("schema_version", 1) >= 2 else [])
        observations = [json.loads(row["body"]) for row in history] if body.get("schema_version", 1) >= 2 else body["observations"]
        for observation in observations:
            if observation["version"] == version:
                if digest(observation["projection"]) != observation["projection_sha256"]:
                    raise Conflict("historical projection hash mismatch")
                return deepcopy(observation["projection"])
        raise KeyError("world version not found")

    def context(self, body: dict, role: str, budget_chars: int = 16000) -> dict:
        entities = []
        result = {"schema_version": 1, "role": role, "case_id": body["case_id"],
                "state_version": body["state_version"], "entities": entities,
                "claims": body["claims"], "relationships": body["relationships"],
                "latest_critique": body.get("critique_history", [])[-1:] or [],
                "controller_feedback": body.get("claim_validation_errors", []),
                "truncated": False,
                "runtime_manifest": {"wired": ["entities", "claims", "relationships", "provenance"],
                                     "dormant": ["vector_memory", "cross_case_enrichment"]}}
        if len(canonical(result)) > budget_chars:
            raise ValueError("required claim and relationship context exceeds budget")
        records = (WorldModel(safe_namespace(body), body["world_model"]).evidence_records()
                   if body.get("world_model") else list(body["entities"].values()))
        # Prioritize receipts and configuration so large documents cannot crowd out authority.
        records.sort(key=lambda r: (r["kind"] == "document", r["evidence_id"]))
        for entity in records:
            latest = body["entities"].get(entity["evidence_id"], entity)
            entities.append({**entity, "query_receipt": latest.get("query_receipt"),
                             "selection_reason": "world_model_case_scoped_evidence"})
            if len(canonical(result)) > budget_chars:
                entities.pop()
                result["truncated"] = True
        # Check the complete envelope rather than just entity payloads.
        if len(canonical(result)) > budget_chars:
            raise ValueError("context exceeds budget")
        return result

    def pending(self) -> list[dict[str, Any]]:
        return [json.loads(r["body"]) for r in self.store.query(
            "SELECT w.body FROM tv_worlds w JOIN (SELECT DISTINCT case_id FROM tv_job_index WHERE status IN ('queued','running')) j ON w.id=j.case_id ORDER BY w.id LIMIT 64")]

    def active_count(self) -> int:
        return self.store.query("SELECT COUNT(*) AS n FROM tv_job_index WHERE status IN ('queued','running')")[0]["n"]
