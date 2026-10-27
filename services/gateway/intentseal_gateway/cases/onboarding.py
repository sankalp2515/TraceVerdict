"""Scoped agent registration and operator-controlled publishing to managed sources."""
from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import Field

from intentseal_core.policy import AgentPolicy, list_policies, load_policy
from intentseal_core.secrets import redact, registry
from ..security import Principal, require
from ..tenancy import refresh
from .models import Strict, canonical, digest

router = APIRouter(tags=["Integration onboarding"])


class AgentRegistration(Strict):
    agent_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    policy: AgentPolicy


class AgentRegistry:
    def __init__(self, store):
        self.store = store
        store.ensure_schema(["CREATE TABLE IF NOT EXISTS tv_agents (agent_id TEXT PRIMARY KEY,tenant_id TEXT NOT NULL,policy TEXT NOT NULL)"])

    def names(self):
        return sorted(set(list_policies()) | {r["agent_id"] for r in self.store.query("SELECT agent_id FROM tv_agents")})

    def load(self, agent):
        rows = self.store.query("SELECT policy FROM tv_agents WHERE agent_id=?", (agent,))
        return AgentPolicy.model_validate_json(rows[0]["policy"]) if rows else load_policy(agent)

    def register(self, body, tenant):
        if body.policy.agent != body.agent_id or body.policy.org != tenant:
            raise ValueError("agent policy identity mismatch")
        if body.agent_id in self.names():
            raise FileExistsError("agent already exists; registration does not overwrite policy")
        serialized = canonical(body.policy.model_dump(mode="json"))
        if redact(serialized) != serialized:
            raise ValueError("redact credentials before registering a policy")
        with self.store.transaction():
            inserted = self.store.execute("INSERT INTO tv_agents VALUES(?,?,?) ON CONFLICT DO NOTHING", (body.agent_id, tenant, serialized))
            if inserted.rowcount != 1:
                raise FileExistsError("agent already exists")


@router.post("/v1/agents", status_code=201)
async def register_agent(body: AgentRegistration, request: Request, p: Principal = require("admin")):
    runtime = request.app.state.engine
    if not hasattr(runtime, "agents"):
        raise HTTPException(409, "agent onboarding requires the case-only application")
    if p.agents is not None and body.agent_id not in p.agents:
        raise HTTPException(403, "agent outside credential scope")
    tenant = body.policy.org if p.all_orgs else p.org
    try:
        runtime.agents.register(body, tenant)
    except FileExistsError:
        raise HTTPException(409, "agent already registered; existing policies are preserved") from None
    except ValueError:
        raise HTTPException(422, "invalid, out-of-scope or unredacted policy") from None
    refresh(request)
    return {"agent_id": body.agent_id, "tenant_id": tenant, "policy_sha256": digest(body.policy.model_dump(mode="json"))}


def publish_records(records):
    """Write only to configured evidence stores. Clients cannot choose URLs or SQL."""
    import psycopg
    groups = {"events": [], "configuration": [], "reference": []}
    for r in records:
        group = "configuration" if r.kind in ("policy", "tools") else "reference" if r.kind == "reference" else "events"
        groups[group].append(r.model_dump(mode="json"))
    if any(not rows for rows in groups.values()):
        raise ValueError("all three source groups are required")
    receipts = []
    for index, (group, rows) in enumerate(groups.items()):
        password = os.getenv(f"TV_{group.upper()}_PASSWORD", "")
        url = os.getenv(f"TRACEVERDICT_{group.upper()}_WRITE_URL", "")
        if password:
            registry.register(password)
        if not url:
            if not password:
                raise RuntimeError("managed source credentials missing")
            kwargs = dict(host="127.0.0.1", port=54331 + index, dbname=group, user="tv_owner", password=password)
        else:
            kwargs = dict(conninfo=url)
        version = digest(rows)
        scope = (rows[0]["tenant_id"], rows[0]["agent_id"], rows[0]["case_id"])
        with psycopg.connect(**kwargs, connect_timeout=10) as conn:
            # Lock the immutable membership version before adding idempotent evidence.
            conn.execute("INSERT INTO case_membership VALUES(%s,%s,%s,%s) ON CONFLICT DO NOTHING", (*scope, version))
            old = conn.execute("SELECT source_version FROM case_membership WHERE tenant_id=%s AND agent_id=%s AND case_id=%s FOR UPDATE", scope).fetchone()
            if old[0] != version:
                raise ValueError("immutable source version changed")
            for row in rows:
                conn.execute("INSERT INTO evidence VALUES(%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                             (*scope, row["evidence_id"], row["kind"], canonical(row)))
        receipts.append({"source": group, "records": len(rows), "version": version})
    return receipts


@router.post("/v1/cases/{cid}/publish-source-records")
async def publish_case(cid: str, request: Request, p: Principal = require("admin")):
    from .api import case_for, service
    if os.getenv("TRACEVERDICT_MANAGED_SOURCES", "false").lower() != "true":
        raise HTTPException(409, "managed source publishing is not enabled; use your governed ingestion pipeline")
    case = case_for(request, p, cid)
    if case["execution_mode"] != "live" or case["status"] != "COLLECTING":
        raise HTTPException(409, "publish only before investigation of a live case")
    records = service(request).source_records(case)
    try:
        receipts = await asyncio.to_thread(publish_records, records)
    except ValueError:
        raise HTTPException(409, "source snapshot conflict or missing source group") from None
    except Exception:
        raise HTTPException(503, "source publication failed; retry is idempotent after dependency recovery") from None
    return {"case_id": cid, "sources": receipts, "investigation_reads": "Zetaris governed view", "published": True}
