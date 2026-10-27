"""Authenticated backend contracts for the independently implemented frontend."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from ..security import Principal, require
from ..tenancy import agent_filter, require_agent, visible_agents
from .models import ApprovalRequest, CandidateRequest, CreateCase, JobRequest
from .repository import graph
from .world_state import Conflict
from .snapshots import ReplayCapture

router = APIRouter(tags=["TraceVerdict"])


@router.get("/v1/operations")
async def operations(request: Request, p: Principal = require("admin")):
    """Scoped queue signals for operators; no prompts, credentials or case payloads."""
    import json
    import time
    scoped, params = agent_filter("w.agent_id", visible_agents(request, p))
    where, values = ("1=1", []) if p.all_orgs else ("w.tenant_id=?", [p.org])
    store = service(request).engine.store
    counts = store.query(
        f"SELECT j.status,COUNT(*) AS records FROM tv_job_index j JOIN tv_worlds w ON j.case_id=w.id "
        f"WHERE {where}{scoped} GROUP BY j.status", (*values, *params))
    active = store.query(
        f"SELECT DISTINCT w.body FROM tv_worlds w JOIN tv_job_index j ON j.case_id=w.id "
        f"WHERE {where}{scoped} AND j.status IN ('queued','running') LIMIT 32", (*values, *params))
    now = time.time()
    jobs = [j for row in active for j in json.loads(row["body"])["jobs"].values()
            if j["status"] in ("queued", "running")]
    queued_ages = [max(0, now - j["created_at"]) for j in jobs if j["status"] == "queued"]
    expired = sum(j["status"] == "running" and j["lease_until"] < now for j in jobs)
    limits = store.query("SELECT max_running FROM tv_scheduler WHERE id=1")
    return {"scope": "authorized tenant and agents", "database_online": store.ping(),
            "jobs_by_status": {row["status"]: row["records"] for row in counts},
            "oldest_queued_age_s": round(max(queued_ages, default=0), 3),
            "expired_running_leases": expired, "queue_attention": max(queued_ages, default=0) > 180 or expired > 0,
            "configured_global_running_limit": limits[0]["max_running"],
            "configured_global_active_limit": 32,
            "limitations": ["Queue signals are not a throughput or latency SLO.",
                            "Provider and whole-platform health require the connections probe."]}


@router.post("/v1/replay-snapshots", status_code=201)
async def capture_snapshot(body: ReplayCapture, request: Request, p: Principal = require("admin")):
    require_agent(request, p, body.agent_id)
    tenant = request.app.state.engine.policy_loader(body.agent_id).org
    try:
        sid, frozen = service(request).snapshots.capture(body, tenant)
    except ValueError:
        raise HTTPException(422, "invalid, unredacted or out-of-scope capture") from None
    return {"snapshot_id": sid, "manifest_sha256": frozen["manifest_sha256"],
            "agent_id": body.agent_id, "scenario_count": len(frozen["scenarios"]),
            "origin": "operator-attested-capture"}


@router.get("/v1/cases")
async def list_cases(request: Request, limit: int = Query(20, ge=1, le=100),
                     cursor: str = Query("", max_length=64), p: Principal = require("project")):
    import json
    scoped, params = agent_filter("agent_id", visible_agents(request, p))
    where, values = ("1=1", []) if p.all_orgs else ("tenant_id=?", [p.org])
    rows = service(request).engine.store.query(
        f"SELECT id,body FROM tv_worlds WHERE {where}{scoped} AND id>? ORDER BY id LIMIT ?",
        (*values, *params, cursor, limit + 1))
    items = []
    for row in rows[:limit]:
        body = json.loads(row["body"])
        items.append({k: body.get(k) for k in ("case_id", "tenant_id", "agent_id", "status", "execution_mode", "created_at", "state_version", "fixture_id")})
    return {"items": items, "next_cursor": rows[limit - 1]["id"] if len(rows) > limit else None}


def service(request: Request):
    return request.app.state.cases


def case_for(request: Request, p: Principal, cid: str) -> dict:
    svc = service(request)
    rows = svc.engine.store.query("SELECT tenant_id, agent_id FROM tv_worlds WHERE id=?", (cid,))
    if not rows or (not p.all_orgs and rows[0]["tenant_id"] != p.org):
        raise HTTPException(404, "case not found")
    require_agent(request, p, rows[0]["agent_id"])
    return svc.world.load(cid, rows[0]["tenant_id"], rows[0]["agent_id"])


def repair_for(request: Request, p: Principal, rid: str) -> tuple[dict, dict]:
    # IDs are case-bound content hashes. Resolve only within the caller's visible cases.
    svc = service(request)
    cid = svc.world.object_case(rid, "repair", None if p.all_orgs else p.org)
    if cid:
        case = case_for(request, p, cid)
        for candidate in case["candidates"]:
            if candidate["candidate_id"] == rid:
                return case, candidate
    raise HTTPException(404, "repair not found")


@router.post("/v1/cases", status_code=201)
async def create_case(body: CreateCase, request: Request, p: Principal = require("project")):
    if getattr(request.app.state, "sample_only", False) and (body.execution_mode != "sample" or body.session_ids):
        raise HTTPException(422, "this server supports synthetic sample cases only")
    require_agent(request, p, body.agent_id)
    tenant = request.app.state.engine.policy_loader(body.agent_id).org
    try:
        return service(request).create(body, tenant)
    except KeyError:
        raise HTTPException(404, "session not found") from None
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None
    except ValueError:
        raise HTTPException(422, "invalid case input") from None


@router.get("/v1/cases/{cid}")
async def get_case(cid: str, request: Request, p: Principal = require("project")):
    return case_for(request, p, cid)


@router.get("/v1/cases/{cid}/graph")
async def get_graph(cid: str, request: Request, p: Principal = require("project")):
    return graph(case_for(request, p, cid))


@router.get("/v1/cases/{cid}/evidence/{eid}")
async def get_evidence(cid: str, eid: str, request: Request, p: Principal = require("project")):
    case = case_for(request, p, cid)
    if eid not in case["entities"]:
        raise HTTPException(404, "evidence not found in case")
    return case["entities"][eid]


@router.get("/v1/cases/{cid}/export")
async def export(cid: str, request: Request, p: Principal = require("project")):
    return service(request).export(case_for(request, p, cid))


@router.get("/v1/cases/{cid}/history/{version}")
async def history(cid: str, version: int, request: Request, p: Principal = require("project")):
    case = case_for(request, p, cid)
    try:
        return service(request).world.at_version(cid, case["tenant_id"], version)
    except KeyError:
        raise HTTPException(404, "case version not found") from None
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/v1/cases/{cid}/source-records")
async def source_records(cid: str, request: Request, p: Principal = require("admin")):
    """Registration material for sponsor onboarding; not a live investigation fallback."""
    return [r.model_dump(mode="json") for r in service(request).source_records(case_for(request, p, cid))]


@router.post("/v1/cases/{cid}/investigate", status_code=202)
async def investigate(cid: str, body: JobRequest, request: Request, p: Principal = require("project")):
    try:
        return service(request).job(case_for(request, p, cid), "investigate", body.idempotency_key)
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/v1/cases/{cid}/jobs/{jid}")
async def job(cid: str, jid: str, request: Request, p: Principal = require("project")):
    case = case_for(request, p, cid)
    if jid not in case["jobs"]:
        raise HTTPException(404, "job not found")
    return case["jobs"][jid]


@router.post("/v1/cases/{cid}/repairs", status_code=201)
async def repairs(cid: str, body: CandidateRequest, request: Request, p: Principal = require("project")):
    try:
        return service(request).add_candidate(case_for(request, p, cid), body)
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None
    except (ValueError, KeyError):
        raise HTTPException(422, "invalid or unsupported repair") from None


@router.post("/v1/repairs/{rid}/validate", status_code=202)
async def validate(rid: str, body: JobRequest, request: Request, p: Principal = require("project")):
    case, candidate = repair_for(request, p, rid)
    try:
        return service(request).job(case, "validate", body.idempotency_key, candidate["candidate_id"])
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/v1/validations/{vid}")
async def validation(vid: str, request: Request, p: Principal = require("project")):
    cid = service(request).world.object_case(vid, "validation", None if p.all_orgs else p.org)
    if cid:
        case = case_for(request, p, cid)
        for report in case["validations"].values():
            if report["validation_id"] == vid:
                return report
    raise HTTPException(404, "validation not found")


@router.post("/v1/repairs/{rid}/approve")
async def approve(rid: str, body: ApprovalRequest, request: Request, p: Principal = require("admin")):
    case, _ = repair_for(request, p, rid)
    try:
        return service(request).approve(case, rid, body.model_dump(), p.name)
    except Conflict as exc:
        raise HTTPException(409, str(exc)) from None
