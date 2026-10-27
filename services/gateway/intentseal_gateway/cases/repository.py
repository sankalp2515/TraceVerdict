"""Case-scoped evidence and a graph whose relationships name their supporting records."""
from __future__ import annotations

from typing import Any

from intentseal_core.secrets import redact

from .models import Evidence, canonical, digest


def evidence(case: dict, kind: str, payload: dict, locator: str, version: str = "1") -> Evidence:
    content_hash = digest(payload)
    eid = "ev_" + digest([case["case_id"], kind, locator, version, content_hash])[:28]
    return Evidence(evidence_id=eid, tenant_id=case["tenant_id"], agent_id=case["agent_id"],
                    case_id=case["case_id"], kind=kind, source_locator=locator, source_version=version,
                    payload=payload, content_sha256=content_hash)


def ingest(case: dict, records: list[Evidence]) -> None:
    """Idempotent canonical evidence projection; immutable originals remain keyed by content."""
    for record in records:
        if (record.case_id, record.tenant_id, record.agent_id) != (case["case_id"], case["tenant_id"], case["agent_id"]):
            raise ValueError("evidence outside case scope")
        if digest(record.payload) != record.content_sha256:
            raise ValueError("evidence content hash mismatch")
        if redact(canonical(record.payload)) != canonical(record.payload):
            raise ValueError("evidence must be redacted before registration")
        value = record.model_dump(mode="json")
        old = case["entities"].get(record.evidence_id)
        if old and {k: v for k, v in old.items() if k != "query_receipt"} != {
                k: v for k, v in value.items() if k != "query_receipt"}:
            raise ValueError("immutable evidence changed")
        case["entities"][record.evidence_id] = value


def validate_claims(case: dict, claims: list[dict]) -> list[str]:
    errors = []
    ids = [c["claim_id"] for c in claims]
    if len(ids) != len(set(ids)):
        errors.append("duplicate claim id")
    for claim in claims:
        if not claim["support_evidence_ids"] or any(eid not in case["entities"] for eid in claim["support_evidence_ids"]):
            errors.append(claim["claim_id"] + ": missing case-scoped support")
        if claim["missing_evidence"]:
            errors.append(claim["claim_id"] + ": unresolved evidence")
    return errors


def critic_context(context: dict) -> dict:
    """Evidence-first read projection; transport receipts/default config are not reasoning context."""
    evidence = {}
    for item in context["entities"]:
        payload = item["payload"]
        if item["kind"] == "policy":
            fields = ("agent", "org", "mode", "content_checks", "contract")
            payload = {k: payload[k] for k in fields if k in payload}
        evidence[item["evidence_id"]] = {"kind": item["kind"], "payload": payload,
                                         "content_sha256": item["content_sha256"]}
    return {"case_id": context["case_id"], "state_version": context["state_version"],
            "claims": context["claims"], "evidence_by_id": evidence,
            "latest_critique": context.get("latest_critique", []), "truncated": context["truncated"]}


def execution_state(action: dict, receipt: dict | None) -> str:
    withheld = action.get("enforced") in ("BLOCK", "ESCALATE")
    if receipt and receipt.get("executed") is True:
        return "contradiction" if withheld else "application-reported-executed"
    if withheld or (receipt and receipt.get("executed") is False):
        return "withheld"
    return "allowed-but-unconfirmed"


def graph(case: dict) -> dict[str, Any]:
    nodes, edges = [], []
    for eid, record in case["entities"].items():
        nodes.append({"id": eid, "type": record["kind"], "source_locator": record["source_locator"],
                      "source_version": record["source_version"], "content_sha256": record["content_sha256"]})
    for claim in case["claims"]:
        cid = "claim:" + claim["claim_id"]
        nodes.append({"id": cid, "type": "claim", "statement": claim["statement"], "status": claim["review_status"]})
        for eid in claim["support_evidence_ids"]:
            if eid in case["entities"]:
                edges.append({"id": digest([eid, cid]), "from": eid, "to": cid, "relation": "supports",
                              "basis": claim["basis"], "style": "solid" if claim["basis"] == "observed" else "dashed",
                              "support_evidence_ids": [eid]})
    # Receipts reference the actual application event; no temporal order is promoted to causation.
    actions = {r["payload"].get("event_id"): eid for eid, r in case["entities"].items() if r["kind"] == "action"}
    for eid, record in case["entities"].items():
        if record["kind"] == "receipt" and (action := actions.get(record["payload"].get("event_id"))):
            edges.append({"id": digest([action, eid]), "from": action, "to": eid,
                          "relation": "application_reports", "basis": "observed", "style": "solid",
                          "support_evidence_ids": [action, eid]})
    # Explicit policy/tool/reference relationships carry the configuration evidence,
    # not a claim that the record's presence proves the policy was enforced.
    for action in actions.values():
        for eid, record in case["entities"].items():
            if record["kind"] in ("task", "policy", "tools", "reference"):
                edges.append({"id": digest([eid, action]), "from": eid, "to": action,
                              "relation": "case_context", "basis": "temporal_context", "style": "dashed",
                              "support_evidence_ids": [eid, action]})
    return {"nodes": nodes, "edges": edges, "limitations": ["Inferred links do not prove causal influence."]}


def compare_snapshots(before: dict, after: dict) -> list[dict]:
    def flatten(value: Any, path: str = "") -> dict:
        if isinstance(value, dict):
            return {k: v for key, item in value.items() for k, v in flatten(item, f"{path}.{key}".strip(".")).items()}
        return {path: value}
    left, right = flatten(before), flatten(after)
    return [{"path": p, "before": left.get(p), "after": right.get(p)}
            for p in sorted(left.keys() | right.keys()) if canonical(left.get(p)) != canonical(right.get(p))]
