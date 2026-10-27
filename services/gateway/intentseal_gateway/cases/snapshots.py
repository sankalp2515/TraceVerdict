"""Immutable replay captures. Trusted operators attest originals; models cannot edit them."""
from __future__ import annotations

from datetime import datetime
import time
import json
from typing import Literal

from pydantic import Field, model_validator

from intentseal_core.policy import AgentPolicy
from intentseal_core.secrets import redact
from .models import Strict, canonical, digest
from .replay_build import replay_build_sha256


class ReplayScenario(Strict):
    id: str = Field(min_length=1, max_length=80)
    category: Literal["unsafe", "utility"]
    split: Literal["development", "acceptance"]
    family: str = Field(default="operator-capture", max_length=80)
    task: str = Field(min_length=1, max_length=4000)
    tool: Literal["send_message", "summarize"]
    args: dict[str, str] = Field(max_length=3)
    allowed: bool
    expected_output: str | None = Field(default=None, max_length=16000)
    document: str | None = Field(default=None, max_length=16000)

    @model_validator(mode="after")
    def local_executor_only(self):
        expected = {"to", "body"} if self.tool == "send_message" else {"text"}
        if set(self.args) != expected or any(len(v) > 16000 for v in self.args.values()):
            raise ValueError("unsupported local replay arguments")
        if self.category == "unsafe" and (self.allowed or self.tool != "send_message"):
            raise ValueError("unsafe acceptance must withhold a send")
        if self.category == "utility" and not self.allowed:
            raise ValueError("utility acceptance must complete the task")
        if self.tool == "summarize" and self.expected_output != self.args["text"]:
            raise ValueError("this executor validates a frozen read artifact, not free-form summary quality")
        return self


class RecordedAction(Strict):
    event_id: str = Field(min_length=1, max_length=128)
    tool: Literal["send_message"]
    args: dict[str, str]
    enforced: Literal["ALLOW", "BLOCK", "ESCALATE", "NEUTRALISE"]


class RecordedReceipt(Strict):
    event_id: str = Field(min_length=1, max_length=128)
    receipt_id: str = Field(min_length=1, max_length=128)
    executed: bool
    executor: str = Field(min_length=1, max_length=128)
    output: str = Field(default="application-reported", max_length=2000)
    outbox_count: int | None = Field(default=None, ge=0)


class ReplayCapture(Strict):
    agent_id: str = Field(min_length=1, max_length=64)
    task: str = Field(min_length=1, max_length=4000)
    document: str = Field(min_length=1, max_length=16000)
    policy: AgentPolicy
    approved_recipients: list[str] = Field(min_length=1, max_length=50)
    action: RecordedAction
    receipt: RecordedReceipt
    source_locator: str = Field(min_length=1, max_length=500)
    source_version: str = Field(min_length=1, max_length=100)
    captured_at: datetime
    model_refs: list[str] = Field(min_length=1, max_length=10)
    tool_build_ref: str = Field(min_length=1, max_length=200)
    scenarios: list[ReplayScenario] = Field(min_length=2, max_length=64)

    @model_validator(mode="after")
    def complete_capture(self):
        if self.captured_at.tzinfo is None:
            raise ValueError("capture timestamp must include timezone")
        if self.policy.agent != self.agent_id or self.receipt.event_id != self.action.event_id:
            raise ValueError("snapshot identity or receipt/action mismatch")
        if len({s.id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("duplicate scenario identity")
        first = self.scenarios[0]
        if first.category != "unsafe" or first.task != self.task or first.args != self.action.args:
            raise ValueError("first scenario must freeze the disputed action and original task")
        if first.document is not None and first.document != self.document:
            raise ValueError("original scenario document must match captured original")
        if any(s.category == "utility" and s.tool == "send_message" and s.args.get("body") != "summary" for s in self.scenarios):
            raise ValueError("utility send must reference the prepared summary marker")
        if not any(s.category == "utility" for s in self.scenarios):
            raise ValueError("a legitimate utility check is required")
        if set(self.action.args) != {"to", "body"}:
            raise ValueError("unsupported recorded action")
        return self


class SnapshotStore:
    def __init__(self, store):
        self.store = store
        store.ensure_schema(["CREATE TABLE IF NOT EXISTS tv_replay_snapshots (id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,"
                             "agent_id TEXT NOT NULL,manifest_sha256 TEXT NOT NULL,body TEXT NOT NULL,received_at REAL NOT NULL)",
                             "CREATE INDEX IF NOT EXISTS tv_snapshot_scope ON tv_replay_snapshots(tenant_id,agent_id)"])

    def put(self, frozen: dict, tenant: str, agent: str) -> str:
        if frozen["policy"]["org"] != tenant or frozen["policy"]["agent"] != agent:
            raise ValueError("snapshot policy is outside scope")
        manifest = {k: v for k, v in frozen.items() if k != "manifest_sha256"}
        hashed = digest(manifest)
        if frozen.get("manifest_sha256") != hashed:
            raise ValueError("snapshot manifest hash mismatch")
        if redact(canonical(frozen)) != canonical(frozen):
            raise ValueError("redact credentials before snapshot registration")
        sid = "snapshot_" + digest([tenant, agent, hashed])[:28]
        self.store.execute("INSERT INTO tv_replay_snapshots VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING",
                           (sid, tenant, agent, hashed, canonical(frozen), time.time()))
        return sid

    def load(self, sid: str, tenant: str, agent: str) -> dict:
        rows = self.store.query("SELECT body,manifest_sha256 FROM tv_replay_snapshots WHERE id=? AND tenant_id=? AND agent_id=?",
                                (sid, tenant, agent))
        if not rows:
            raise KeyError("snapshot not found in scope")
        value = json.loads(rows[0]["body"])
        if digest({k: v for k, v in value.items() if k != "manifest_sha256"}) != rows[0]["manifest_sha256"]:
            raise ValueError("stored snapshot integrity failure")
        return value

    def capture(self, body: ReplayCapture, tenant: str) -> tuple[str, dict]:
        frozen = {"version": body.source_version, "origin": "operator-attested-capture",
                  "policy": body.policy.model_dump(mode="json"), "task": body.task, "document": body.document,
                  "reference": {"approved_recipients": body.approved_recipients, "outbox": "in_memory_only"},
                  "captured_action": body.action.model_dump(mode="json"),
                  "captured_receipt": body.receipt.model_dump(mode="json", exclude_none=True),
                  "source_locator": body.source_locator, "captured_at": body.captured_at.isoformat(),
                  "model_refs": body.model_refs, "tool_build_ref": body.tool_build_ref,
                  "scenarios": [s.model_dump(mode="json", exclude_none=True) for s in body.scenarios],
                  "executor": "local-outbox-v3-typed-action", "replay_build_sha256": replay_build_sha256(), "trial_count": 1,
                  "limitations": ["Producer-attested originals, not independent verification of source authenticity."]}
        frozen["manifest_sha256"] = digest(frozen)
        return self.put(frozen, tenant, body.agent_id), frozen
