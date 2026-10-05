"""Gateway API (API-1…API-11) and LLM proxy mount. Run: uvicorn asg_gateway.app:app --port 8000

All surfaces share one Core Engine instance (CORE-1). OpenAPI docs at /docs (API-10).
"""

from __future__ import annotations

import base64
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from asg_core.config import repo_root
from asg_core.engine import Engine
from asg_core.llm.router import Router
from asg_core.policy import load_policy

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


def build_engine() -> Engine:
    router = Router()
    return Engine(router=router, store=router.store, tier0_timeout_s=float(os.environ.get("ASG_EXTRACT_TIMEOUT_S", "10")))


def create_app(engine: Engine | None = None, reports_dir: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.engine = engine or build_engine()
        app.state.keys = KeyRing()
        app.state.reports = reports_dir or repo_root() / "eval" / "reports"
        app.state.started = time.time()
        yield
        router = getattr(app.state.engine, "router", None)
        if router is not None and hasattr(router, "aclose"):
            await router.aclose()

    app = FastAPI(title="Agent Security Gateway API (working name)", version="0.1.0", lifespan=lifespan,
                  description="Inspect content, check actions, replay sessions. Rules decide; AI advises.")
    origins = [o.strip() for o in os.environ.get("ASG_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "X-API-Key", "Content-Type", "X-Agent-Id", "X-Session-Id"])
    app.add_middleware(BodySizeLimit)

    @app.get("/healthz", tags=["ops"])
    async def healthz(request: Request) -> dict[str, Any]:
        return {"ok": True, "uptime_s": round(time.time() - request.app.state.started, 1)}

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
                        agent: str | None = None, since: float | None = None,
                        limit: int = Query(100, le=500), p: Principal = require("public")) -> list[dict[str, Any]]:
        return request.app.state.engine.logger.decisions(decision=decision, label=label, agent=agent, since=since, limit=limit)

    # ---- API-5 scorecard ----------------------------------------------------------------------
    @app.get("/v1/scorecard/{agent}", tags=["evidence"])
    async def scorecard(agent: str, request: Request, p: Principal = require("public")) -> dict[str, Any]:
        d: Path = request.app.state.reports
        reports = sorted(d.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True) if d.exists() else []
        if not reports:
            raise HTTPException(404, "no evaluation report yet")
        latest = {}
        for f in reports:
            rep = json.loads(f.read_text(encoding="utf-8"))
            key = f"{rep.get('suite', 'broad')}:{rep.get('protection')}"
            latest.setdefault(key, {"file": f.name, **rep})
        return {"agent": agent, "reports": latest}

    # ---- API-6 policy (read) ------------------------------------------------------------------
    @app.get("/v1/policies/{agent}", tags=["policy"])
    async def policy(agent: str, p: Principal = require("public")) -> dict[str, Any]:
        pol = load_policy(agent).model_dump(mode="json")
        pol["sensitive_data"]["canaries"] = [c if c == "from_env" else "[REDACTED]" for c in pol["sensitive_data"]["canaries"]]
        return pol

    # ---- API-11 costs (P1) --------------------------------------------------------------------
    @app.get("/v1/costs", tags=["evidence"])
    async def costs(request: Request, days: int = Query(7, le=90), p: Principal = require("public")) -> dict[str, Any]:
        since = time.time() - days * 86400
        rows = request.app.state.engine.store.query(
            "SELECT role, provider, model, COUNT(*) AS calls, SUM(cached) AS cached, SUM(input_tokens) AS input_tokens, "
            "SUM(output_tokens) AS output_tokens, ROUND(SUM(est_cost_usd), 6) AS est_cost_usd, ROUND(AVG(latency_ms)) AS avg_latency_ms "
            "FROM llm_usage WHERE ts >= ? GROUP BY role, provider, model ORDER BY calls DESC", (since,))
        return {"days": days, "by_model": rows}

    # ---- API-7 demo runner --------------------------------------------------------------------
    @app.get("/demo/scenarios", tags=["demo"])
    async def scenarios(p: Principal = require("public")) -> list[dict[str, Any]]:
        from .demo import list_scenarios
        return list_scenarios()

    @app.post("/demo/run", tags=["demo"])
    async def demo_run(body: DemoRequest, request: Request, p: Principal = require("public")) -> dict[str, Any]:
        from .demo import run_scenario
        try:
            return await run_scenario(request.app.state.engine, body.scenario_id, body.protection)
        except KeyError:
            raise HTTPException(404, f"unknown scenario '{body.scenario_id}'") from None

    from .proxy import router as proxy_router
    app.include_router(proxy_router)
    return app


app = create_app()
