"""Strict API contracts. Models propose; persisted, deterministic gates decide."""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CreateCase(Strict):
    agent_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    session_ids: list[str] = Field(default_factory=list, max_length=10)
    fixture_id: Literal["supplier-contact", "invoice-forward", "report-notify"] | None = None
    snapshot_id: str | None = Field(default=None, pattern=r"^snapshot_[a-f0-9]{28}$")
    execution_mode: Literal["sample", "live"] = Field(
        default_factory=lambda: "sample" if os.environ.get("SAMPLE_MODE", "").lower() == "true" else "live")
    idempotency_key: str = Field(min_length=8, max_length=128)


class Evidence(Strict):
    evidence_id: str
    tenant_id: str
    agent_id: str
    case_id: str
    kind: Literal["task", "document", "action", "receipt", "policy", "tools", "reference", "event"]
    source_locator: str
    source_version: str
    payload: dict[str, Any]
    content_sha256: str
    query_receipt: dict[str, Any] | None = None


class Claim(Strict):
    claim_id: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=2000)
    support_evidence_ids: list[str] = Field(min_length=1, max_length=12)
    basis: Literal["observed", "inferred", "temporal_context"]
    competing_explanations: list[str] = Field(default_factory=list, max_length=5)
    missing_evidence: list[str] = Field(default_factory=list, max_length=10)
    review_status: Literal["proposed", "accepted", "disputed", "unresolved"] = "proposed"


class Explanation(Strict):
    claims: list[Claim] = Field(min_length=1, max_length=12)
    uncertainty: list[str] = Field(default_factory=list, max_length=12)


class ClaimCheck(Strict):
    claim_id: str = Field(min_length=1, max_length=128)
    outcome: Literal["supported", "unsupported", "uncertain"]
    support_evidence_ids: list[str] = Field(max_length=12, description="Case evidence IDs actually checked; include every cited ID for a supported claim")
    reason: str = Field(min_length=1, max_length=500)


class CriticSubmission(Strict):
    checks: list[ClaimCheck] = Field(min_length=1, max_length=12, description="Exactly one explicit verdict for each input claim")
    reason: str = Field(max_length=2000)


class Critique(Strict):
    disputed_claim_ids: list[str] = Field(max_length=12)
    reason: str = Field(max_length=2000)
    request_evidence_kinds: list[Literal["policy", "receipt", "reference", "tools"]] = Field(default_factory=list)
    checks: list[ClaimCheck] = Field(default_factory=list)


class Operation(Strict):
    path: Literal["contract.mode", "contract.out_of_scope", "tools.send_message.allowed_recipients"]
    value: Literal["enforce", "block", "escalate"] | list[str]


class CandidateRequest(Strict):
    operations: list[Operation] = Field(min_length=1, max_length=3)
    rationale_claim_ids: list[str] = Field(min_length=1, max_length=12)
    expected_control_effect: str = Field(min_length=1, max_length=1000)


class JobRequest(Strict):
    idempotency_key: str = Field(min_length=8, max_length=128)


class ApprovalRequest(Strict):
    base_policy_sha256: str
    patch_sha256: str
    validation_report_sha256: str


class TestOutcome(Strict):
    scenario_id: str
    category: Literal["unsafe", "utility"]
    execution_mode: Literal["fixed_action", "deterministic_task", "end_to_end"]
    expected_behavior: str
    observed_behavior: str
    outcome: Literal["pass", "fail", "error", "unknown", "resisted"]
    decision_event_id: str | None = None
    application_receipt: dict[str, Any] | None = None
    policy_rule: str | None = None
    duration_ms: float
