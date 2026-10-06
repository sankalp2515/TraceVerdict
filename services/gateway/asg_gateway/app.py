"""Gateway API (API-1…API-11) and LLM proxy mount. Run: uvicorn asg_gateway.app:app --port 8000

All surfaces share one Core Engine instance (CORE-1). OpenAPI docs at /docs (API-10).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from asg_core.config import repo_root
from asg_core.costs import overhead, usage_by_role
from asg_core.engine import Engine
from asg_core.llm.router import Router
from asg_core.policy import AgentPolicy, load_policy, save_policy

from .security import BodySizeLimit, KeyRing, Principal, require


class InspectRequest(BaseModel):
    content: str | None = None
    content_b64: str | None = Field(None, description="binary files (PDF, DOCX, images) as base64")
    filename: str | None = None
    source: str = "user"
    agent_id: str
    session_id: str | None = None


class ActionRequest(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    agent_id: str
    session_id: str | None = None


class SessionRequest(BaseModel):
    agent_id: str
    user_ref: str | None = None
    task: str = ""
    trusted: dict[str, Any] = Field(default_factory=dict)


class DemoRequest(BaseModel):
    scenario_id: str
    protection: str = Field("on", pattern="^(on|off)$")


class FeedbackRequest(BaseModel):
    verdict: str = Field(..., pattern="^(attack|false_positive)$")
    event_id: str | None = None
    content: str | None = Field(None, description="when the event is no longer in recent memory")
    agent_id: str = "*"
    labels: list[str] = Field(default_factory=list)
    note: str = ""


class ApprovalRequest(BaseModel):
    approve: bool
    note: str = ""


access = logging.getLogger("asg.access")


def _percentile(values: list[float], q: float) -> float | None:
    values = sorted(v for v in values if v is not None)
    return round(values[min(len(values) - 1, int(q * len(values)))], 1) if values else None


def build_engine() -> Engine:
    router = Router()
    return Engine(router=router, store=router.store, tier0_timeout_s=float(os.environ.get("ASG_EXTRACT_TIMEOUT_S") or "10"))


def create_app(engine: Engine | None = None, reports_dir: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or build_engine()
        if engine is None:   # load classifier + OCR before the first request (no cold-start degraded decisions)
            import asyncio

            from asg_sdk.guard import _warm_up
            await asyncio.to_thread(_warm_up)
        app.state.keys = KeyRing()
        # Ephemeral key for the demo runner's own calls to the proxy (S9); random per process, never exposed.
        import secrets as _secrets
        app.state.internal_key = _secrets.token_urlsafe(24)
        app.state.keys.add(app.state.internal_key, Principal("internal-demo", "project"))
        app.state.reports = reports_dir or repo_root() / "eval" / "reports"
        app.state.started = time.time()
        yield
        router = getattr(app.state.engine, "router", None)
        if router is not None and hasattr(router, "aclose"):
            await router.aclose()

    app = FastAPI(title="IntentSeal Gateway API", version="0.1.0", lifespan=lifespan,
                  description="Keep AI agents inside the user's intent. Inspect content, check actions, replay sessions. Rules decide; AI advises.")
    origins = [o.strip() for o in os.environ.get("ASG_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "DELETE"],
                       allow_headers=["Authorization", "X-API-Key", "Content-Type", "X-Agent-Id", "X-Session-Id",
                                      "X-Request-Id"], expose_headers=["X-Request-Id"])
    app.add_middleware(BodySizeLimit)

    @app.middleware("http")
    async def request_ids(request: Request, call_next):
        # Observability (NFR §12): one id per request, echoed back and written to the structured access log.
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:16]
        t0 = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-Id"] = rid
        access.info(json.dumps({"request_id": rid, "method": request.method, "path": request.url.path,
                                "status": response.status_code, "ms": round((time.perf_counter() - t0) * 1000, 1),
                                "session_id": request.headers.get("x-session-id")}))
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)[:200] or "invalid request"}, status_code=422)

    @app.get("/healthz", tags=["ops"])
    async def healthz(request: Request) -> dict[str, Any]:
        return {"ok": True, "uptime_s": round(time.time() - request.app.state.started, 1)}

    @app.get("/v1/whoami", tags=["ops"])
    async def whoami(p: Principal = require("public")) -> dict[str, str]:
        """Which key is this? Lets the Console confirm a reviewer key is admin-scoped before showing reviewer actions."""
        return {"name": p.name, "scope": p.scope}

    # ---- API-1 inspect ------------------------------------------------------------------------
    @app.post("/v1/inspect", tags=["engine"])
    async def inspect(body: InspectRequest, request: Request, p: Principal = require("project")) -> dict[str, Any]:
        if body.content is None and body.content_b64 is None:
            raise HTTPException(422, "provide content or content_b64")
        try:
            data: bytes | str = base64.b64decode(body.content_b64, validate=True) if body.content_b64 else body.content  # type: ignore[assignment]
        except ValueError:
            raise HTTPException(422, "content_b64 is not valid base64") from None
        r = await request.app.state.engine.inspect(data, body.source, body.agent_id, session_id=body.session_id,
                                                   filename=body.filename)
        return r.model_dump(mode="json")

    # ---- API-2 action check -------------------------------------------------------------------
    @app.post("/v1/actions/check", tags=["engine"])
    async def check(body: ActionRequest, request: Request, p: Principal = require("project")) -> dict[str, Any]:
        r = await request.app.state.engine.check_action(body.tool, body.args, body.agent_id, session_id=body.session_id)
        return r.model_dump(mode="json")

    # ---- API-3 sessions -----------------------------------------------------------------------
    @app.post("/v1/sessions", tags=["sessions"])
    async def new_session(body: SessionRequest, request: Request, p: Principal = require("project")) -> dict[str, str]:
        s = request.app.state.engine.start_session(body.agent_id, user_ref=body.user_ref, task=body.task, trusted=body.trusted)
        return {"session_id": s.session_id}

    @app.get("/v1/sessions/{session_id}/events", tags=["sessions"])
    async def session_events(session_id: str, request: Request, p: Principal = require("public")) -> list[dict[str, Any]]:
        return request.app.state.engine.logger.session_events(session_id)

    # ---- API-4 decisions feed -----------------------------------------------------------------
    @app.get("/v1/decisions", tags=["evidence"])
    async def decisions(request: Request, decision: str | None = None, label: str | None = None,
                        agent: str | None = None, since: float | None = None, before: float | None = None,
                        limit: int = Query(100, ge=1, le=500), p: Principal = require("public")) -> list[dict[str, Any]]:
        return request.app.state.engine.logger.decisions(decision=decision, label=label, agent=agent, since=since,
                                                         limit=limit, before=before)

    # ---- API-5 scorecard ----------------------------------------------------------------------
    @app.get("/v1/scorecard/{agent}", tags=["evidence"])
    async def scorecard(agent: str, request: Request, p: Principal = require("public")) -> dict[str, Any]:
        d: Path = request.app.state.reports
        reports = sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True) if d.exists() else []
        if not reports:
            raise HTTPException(404, "no evaluation report yet")
        latest, summary = {}, None
        for f in reports:
            rep = json.loads(f.read_text(encoding="utf-8"))
            if rep.get("kind") == "summary":   # grid claim + headline metrics (asg_eval.summary)
                summary = summary or {"file": f.name, **rep}
                continue
            key = f"{rep.get('suite', 'broad')}:{rep.get('protection')}"
            latest.setdefault(key, {"file": f.name, **rep})
        return {"agent": agent, "summary": summary, "reports": latest}

    # ---- API-6 policy (read) ------------------------------------------------------------------
    @app.get("/v1/policies/{agent}", tags=["policy"])
    async def policy(agent: str, p: Principal = require("public")) -> dict[str, Any]:
        pol = load_policy(agent).model_dump(mode="json")
        pol["sensitive_data"]["canaries"] = [c if c == "from_env" else "[REDACTED]" for c in pol["sensitive_data"]["canaries"]]
        return pol

    # ---- API-11 costs (P1) --------------------------------------------------------------------
    @app.get("/v1/costs", tags=["evidence"])
    async def costs(request: Request, days: int = Query(7, le=90), p: Principal = require("public")) -> dict[str, Any]:
        rows = usage_by_role(request.app.state.engine.store, time.time() - days * 86400)
        return {"days": days, "by_model": rows, "overhead": overhead(rows)}

    @app.get("/v1/costs/{agent}", tags=["evidence"])
    async def agent_costs(agent: str, request: Request, days: int = Query(7, le=90),
                          p: Principal = require("public")) -> dict[str, Any]:
        """Security spend attributed to one agent: decisions and judge tokens/cost by tier (CORE-14)."""
        since = time.time() - days * 86400
        rows = request.app.state.engine.store.query(
            "SELECT tier, COUNT(*) AS decisions, SUM(input_tokens) AS judge_input_tokens, ROUND(SUM(est_cost), 6) AS est_cost_usd, "
            "SUM(degraded) AS degraded, SUM(budget_degraded) AS budget_degraded FROM decisions "
            "WHERE agent_id = ? AND created_at >= ? GROUP BY tier ORDER BY tier", (agent, since))
        return {"agent": agent, "days": days, "by_tier": rows}

    # ---- API-6 policy write (admin, P1) -------------------------------------------------------
    @app.put("/v1/policies/{agent}", tags=["policy"])
    async def put_policy(agent: str, body: dict[str, Any], p: Principal = require("admin")) -> dict[str, Any]:
        """Replace an agent's policy. Validated against the policy schema, version bumped, written atomically."""
        old = load_policy(agent)
        # GET returns literal canaries as "[REDACTED]"; a round-tripped policy keeps the stored values, never the mask.
        sd = dict(body.get("sensitive_data") or {})
        if "[REDACTED]" in (sd.get("canaries") or []):
            literal = [c for c in old.sensitive_data.canaries if c != "from_env"]
            sd["canaries"] = [c for c in sd["canaries"] if c != "[REDACTED]"] + [c for c in literal if c not in sd["canaries"]]
            body = {**body, "sensitive_data": sd}
        try:
            new = AgentPolicy.model_validate({**body, "agent": agent})
        except ValidationError as e:
            raise HTTPException(422, json.loads(e.json(include_url=False))[:5]) from None
        new.version = str(int(old.version) + 1) if old.version.isdigit() else old.version + ".1"
        save_policy(new)
        access.info(json.dumps({"event": "policy_updated", "agent": agent, "version": new.version, "by": p.name}))
        return {"agent": agent, "version": new.version, "mode": new.mode}

    # ---- CON-8 reviewer feedback -> trainability memory (fingerprints only) --------------------
    @app.post("/v1/feedback", tags=["review"])
    async def feedback(body: FeedbackRequest, request: Request, p: Principal = require("admin")) -> dict[str, Any]:
        if not body.event_id and not body.content:
            raise HTTPException(422, "provide event_id or content")
        try:
            mid = request.app.state.engine.feedback(body.verdict, event_id=body.event_id, content=body.content,
                                                    agent_id=body.agent_id, labels=body.labels,
                                                    origin=f"reviewer:{p.name}", note=body.note)
        except KeyError:
            raise HTTPException(404, "event is no longer in recent memory; send the content instead") from None
        if mid is None:
            raise HTTPException(422, "content too short to fingerprint safely")
        return {"memory_id": mid, "verdict": body.verdict}

    @app.get("/v1/memory", tags=["review"])
    async def memory(request: Request, kind: str | None = Query(None, pattern="^(attack|benign)$"),
                     p: Principal = require("public")) -> dict[str, Any]:
        m = request.app.state.engine.memory
        return {"stats": m.stats(), "entries": m.entries(kind)}

    @app.delete("/v1/memory/{memory_id}", tags=["review"])
    async def forget(memory_id: str, request: Request, p: Principal = require("admin")) -> dict[str, bool]:
        if not request.app.state.engine.memory.remove(memory_id):
            raise HTTPException(404, "unknown memory entry")
        return {"removed": True}

    # ---- CON-9 approvals inbox (ESCALATE decisions) ------------------------------------------
    @app.get("/v1/approvals", tags=["review"])
    async def approvals(request: Request, status: str | None = Query("pending", pattern="^(pending|approved|denied)$"),
                        agent: str | None = None, p: Principal = require("public")) -> list[dict[str, Any]]:
        return request.app.state.engine.logger.approvals(status=status, agent=agent)

    @app.post("/v1/approvals/{event_id}", tags=["review"])
    async def resolve(event_id: str, body: ApprovalRequest, request: Request, p: Principal = require("admin")) -> dict[str, Any]:
        """Approve or deny one escalated action. An approval lets the same call in the same session run once."""
        if not request.app.state.engine.logger.resolve_approval(event_id, body.approve, p.name, body.note):
            raise HTTPException(404, "no pending approval with this id")
        return {"event_id": event_id, "status": "approved" if body.approve else "denied"}

    # ---- Observability (NFR §12) -------------------------------------------------------------
    @app.get("/v1/metrics", tags=["ops"])
    async def metrics(request: Request, hours: float = Query(24, gt=0, le=24 * 30),
                      p: Principal = require("public")) -> dict[str, Any]:
        """Decisions by type and rule, tier escalation rate, latency p50/p95 by tier, provider errors, memory."""
        e = request.app.state.engine
        since = time.time() - hours * 3600
        rows = e.store.query("SELECT d.decision, d.policy_rule, d.tier, d.latency_ms, d.degraded, d.labels, ev.kind "
                             "FROM decisions d JOIN events ev ON ev.id = d.event_id WHERE d.created_at >= ?", (since,))
        content = [r for r in rows if r["kind"] == "content_in"]
        count = lambda key: {k: sum(1 for r in rows if r[key] == k) for k in sorted({r[key] for r in rows})}
        labels: dict[str, int] = {}
        for r in rows:
            for label in json.loads(r["labels"] or "[]"):
                labels[label] = labels.get(label, 0) + 1
        latency = lambda rs: {"n": len(rs), "p50": _percentile([r["latency_ms"] for r in rs], 0.5),
                              "p95": _percentile([r["latency_ms"] for r in rs], 0.95)}
        judged = sum(1 for r in content if r["tier"] == 2)
        return {
            "window_hours": hours, "decisions": len(rows), "by_decision": count("decision"),
            "by_rule": count("policy_rule"), "by_label": dict(sorted(labels.items())),
            "inspections": {"n": len(content), "escalated_to_judge": judged,
                            "escalation_rate": round(judged / len(content), 3) if content else None,
                            "degraded": sum(1 for r in content if r["degraded"])},
            "latency_ms": {"fast_path": latency([r for r in content if (r["tier"] or 0) < 2]),
                           "judge_path": latency([r for r in content if r["tier"] == 2])},
            "providers": e.store.query("SELECT provider, status, COUNT(*) AS n FROM llm_usage WHERE ts >= ? "
                                       "GROUP BY provider, status ORDER BY provider, status", (since,)),
            "memory": e.memory.stats(), "approvals_pending": len(e.logger.approvals("pending")),
        }

    # ---- API-7 demo runner --------------------------------------------------------------------
    @app.get("/demo/scenarios", tags=["demo"])
    async def scenarios(p: Principal = require("public")) -> list[dict[str, Any]]:
        from .demo import list_scenarios
        return list_scenarios()

    @app.post("/demo/run", tags=["demo"])
    async def demo_run(body: DemoRequest, request: Request, p: Principal = require("public")) -> dict[str, Any]:
        from .demo import run_scenario
        try:
            return await run_scenario(request.app.state.engine, body.scenario_id, body.protection, app=request.app)
        except KeyError:
            raise HTTPException(404, f"unknown scenario '{body.scenario_id}'") from None

    from .proxy import router as proxy_router
    app.include_router(proxy_router)
    return app


app = create_app()
