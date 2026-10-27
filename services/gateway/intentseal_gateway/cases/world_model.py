"""Meterless World Model specification implemented for provenance-backed case state.

Canonical events are durable inside the case's CAS aggregate. Projections are rebuilt
from those events, never persisted as an independently writable source of truth.
See docs/METERLESS_WORLD_MODEL.md for scope, upstream revision and conformance.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import re
import unicodedata

from .models import canonical, digest


def normalize_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    return " ".join("".join(c for c in normalized if not unicodedata.combining(c)
                           and c not in "\u200b\u200c\u200d\ufeff").lower().split())


def entity_id_from_name(kind: str, name: str) -> str:
    return "ent_" + hashlib.sha256(f"{kind}:{normalize_name(name)}".encode()).hexdigest()[:16]


def decide(similarity: float, auto_merge_at: float = .85, review_lower: float = .82) -> str:
    if not 0 <= similarity <= 1:
        raise ValueError("invalid similarity")
    return "auto-merge" if similarity >= auto_merge_at else "review" if similarity >= review_lower else "new"


def provenance(value: dict | None) -> dict:
    if not isinstance(value, dict) or not value.get("kind") or not value.get("at"):
        raise ValueError("provenance kind and at are required")
    datetime.fromisoformat(value["at"].replace("Z", "+00:00"))
    return deepcopy(value)


class WorldModel:
    def __init__(self, namespace: str, data: dict | None = None, clock: str | None = None):
        if not namespace:
            raise ValueError("namespace required")
        self.namespace = namespace
        self.data = data if data is not None else {"schema_version": 1, "events": []}
        if self.data.get("schema_version") != 1:
            raise ValueError("unsupported world model schema")
        self.clock = clock
        self.entities: dict[str, dict] = {}
        self.contexts: dict[str, dict] = {}
        self.relationships: dict[str, dict] = {}
        self.observations: dict[str, dict] = {}
        for index, event in enumerate(self.data["events"], 1):
            if event["seq"] != index or digest(event["payload"]) != event["payload_sha256"]:
                raise ValueError("corrupt canonical world event")
            self._apply(event["kind"], event["payload"])

    def _apply(self, kind: str, payload: dict) -> None:
        if kind == "upsertEntity":
            self.entities[payload["id"]] = deepcopy(payload)
        elif kind == "upsertContext":
            self.contexts[payload["id"]] = deepcopy(payload)
        elif kind == "observation":
            self.observations[payload["externalId"]] = deepcopy(payload)
        elif kind == "relate":
            self.relationships[payload["id"]] = deepcopy(payload)
            related = sorted([r for r in self.relationships.values() if (r["from"], r["type"], r.get("context")) ==
                              (payload["from"], payload["type"], payload.get("context"))], key=lambda r: r["validFrom"])
            for old, new in zip(related, related[1:]):
                if old.get("validTo") is None or old["validTo"] > new["validFrom"]:
                    old["validTo"] = new["validFrom"]
        else:
            raise ValueError("unknown canonical event kind")

    def _append(self, kind: str, payload: dict) -> None:
        self.data["events"].append({"seq": len(self.data["events"]) + 1, "kind": kind,
                                    "payload": deepcopy(payload), "payload_sha256": digest(payload)})
        self._apply(kind, payload)

    def upsert_entity(self, value: dict) -> dict:
        source = provenance(value.get("source"))
        kind = value["type"]
        external = value.get("externalKey")
        name = value.get("name") or value.get("attrs", {}).get("name")
        if not external and not name:
            raise ValueError("entity name or external key required")
        eid = f"{kind}:{external['system']}:{external['id']}" if external else entity_id_from_name(kind, name)
        old = self.entities.get(eid)
        entity = {"id": eid, "type": kind, "attrs": deepcopy(value.get("attrs", {})), "source": source,
                  "createdAt": old["createdAt"] if old else source["at"], "updatedAt": source["at"],
                  "schemaVersion": 1, "state": value.get("state", "active")}
        if name:
            entity["name"] = name
        if old != entity:
            self._append("upsertEntity", entity)
        return deepcopy(entity)

    def upsert_context(self, value: dict) -> dict:
        source = provenance(value.get("source"))
        attrs = deepcopy(value.get("attrs", {}))
        key = value.get("externalKey")
        cid = (f"{value['type']}:{key['system']}:{key['id']}" if key else
               "ctx_" + digest([value["type"], attrs, value.get("parent")])[:16])
        context = {"id": cid, "type": value["type"], "attrs": attrs, "source": source, "schemaVersion": 1}
        if self.contexts.get(cid) != context:
            self._append("upsertContext", context)
        return deepcopy(context)

    def ingest(self, observations: list[dict]) -> dict:
        before = self.state_shape_canonical()
        processed = skipped = 0
        for raw in observations:
            source = provenance(raw.get("source"))
            value = deepcopy(raw)
            if not value.get("externalId") or not value.get("at"):
                raise ValueError("observation identity and timestamp required")
            if self.observations.get(value["externalId"]) == value:
                skipped += 1
                continue
            # Every entity write carries the observation's provenance.
            for item in value.get("entities", []):
                self.upsert_entity({**item, "source": source})
            self._append("observation", value)
            processed += 1
        return {"changed": before != self.state_shape_canonical(), "processed": processed, "skippedUnchanged": skipped}

    def relate(self, value: dict) -> dict:
        source = provenance(value.get("source"))
        if value["from"] not in self.entities or value["to"] not in self.entities:
            raise ValueError("relationship endpoints must exist")
        valid_from = value.get("validFrom") or source["at"]
        rid = "rel_" + digest([value["from"], value["type"], value["to"], value.get("context"), valid_from])[:16]
        if rid not in self.relationships:
            self._append("relate", {**deepcopy(value), "source": source, "id": rid, "validFrom": valid_from,
                                    "schemaVersion": 1})
        return deepcopy(self.relationships[rid])

    def neighbors(self, eid: str, *, via: str | None = None, at: str | None = None) -> list[dict]:
        result = {}
        for edge in self.relationships.values():
            if edge["from"] != eid or (via is not None and edge["type"] != via):
                continue
            valid = (edge["validFrom"] <= at and (not edge.get("validTo") or at < edge["validTo"])) if at else not edge.get("validTo")
            if valid:
                result[edge["to"]] = self.entities[edge["to"]]
        return deepcopy(list(result.values()))

    def audit(self) -> list[dict]:
        return [{"seq": e["seq"], "kind": e["kind"], "payload_sha256": e["payload_sha256"]} for e in self.data["events"]]

    def state_shape_canonical(self) -> str:
        return canonical({"entities": self.entities, "contexts": self.contexts,
                          "relationships": self.relationships, "observations": self.observations})

    def ingest_evidence(self, records: list[dict], at: float, case_id: str) -> None:
        timestamp = datetime.fromtimestamp(at, timezone.utc).isoformat()
        observations = []
        for record in records:
            stable = {k: v for k, v in record.items() if k != "query_receipt"}
            observations.append({"externalId": record["evidence_id"], "at": timestamp,
                "source": {"kind": "case-evidence", "at": timestamp, "url": record["source_locator"],
                           "version": record["source_version"], "runId": case_id},
                "entities": [{"type": "evidence", "externalKey": {"system": "traceverdict", "id": record["evidence_id"]},
                              "attrs": {"record": stable}}]})
        self.ingest(observations)

    def evidence_records(self) -> list[dict]:
        return [deepcopy(entity["attrs"]["record"]) for entity in self.entities.values()
                if entity["type"] == "evidence" and "record" in entity["attrs"]]


def safe_namespace(case: dict) -> str:
    return ":".join(re.sub(r"[^A-Za-z0-9_.-]", "_", case[k]) for k in ("tenant_id", "agent_id", "case_id"))
