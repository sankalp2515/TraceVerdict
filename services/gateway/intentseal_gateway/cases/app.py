"""Case investigation service: real sponsor paths, no dummy enforcement endpoints.

Connected applications use the separate IntentSeal gateway/SDK for synchronous
enforcement. This service owns case analysis, bounded local replay and review.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from intentseal_core.config import load_env
from intentseal_core.logger import DecisionLogger
from intentseal_core.secrets import registry
from intentseal_core.store import Store
from ..security import BodySizeLimit, KeyRing, Principal, require
from ..tenancy import can_see
from .api import router
from .service import CaseService
from .sessions import SessionStore, router as sessions_router
from .onboarding import AgentRegistry, router as onboarding_router

load_env()
ORIGINS = [x.strip() for x in (os.environ.get("INTENTSEAL_CORS_ORIGINS") or
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3001,http://127.0.0.1:3001").split(",") if x.strip()]


class CaseRuntime:
    def __init__(self, store):
        self.store = store
        self.logger = DecisionLogger(store)
        self.agents = AgentRegistry(store)
        self.policy_loader = self.agents.load

    def list_agents(self):
        return self.agents.names()

    def has_policy(self, agent):
        return agent in self.list_agents()


@asynccontextmanager
async def lifespan(app):
    load_env()
    # Local generated credentials are mapped in memory, never baked into an image.
    if not os.environ.get("INTENTSEAL_API_KEYS"):
        admin = os.environ.get("TRACEVERDICT_ADMIN_KEY")
        project = os.environ.get("TRACEVERDICT_PROJECT_KEY")
        if not admin or not project:
            raise RuntimeError("Configure application project and reviewer credentials")
        registry.register(admin)
        registry.register(project)
        os.environ["INTENTSEAL_API_KEYS"] = f"reviewer:{admin}:admin:default,developer:{project}:project:default"
    target = os.environ.get("TRACEVERDICT_DB_URL", "data/traceverdict.db")
    if not target.startswith(("postgres://", "postgresql://")):
        Path(target).parent.mkdir(parents=True, exist_ok=True)
    store = Store(target)
    app.state.keys = KeyRing()
    app.state.engine = CaseRuntime(store)
    app.state.sessions = SessionStore(store, app.state.keys, ORIGINS)
    app.state.cases = CaseService(app.state.engine)
    app.state.sample_only = False
    recovery = asyncio.create_task(app.state.cases.recover())
    try:
        yield
    finally:
        recovery.cancel()
        await asyncio.gather(recovery, return_exceptions=True)
        await app.state.cases.close()
        store._conn.close()


app = FastAPI(title="TraceVerdict case API", version="0.2.0", lifespan=lifespan,
    description="Evidence-backed investigation, bounded sandbox repair validation, and human review. Approval exports a recommendation; it never deploys a production patch.")
app.add_middleware(BodySizeLimit)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
    allow_methods=["GET", "POST"], allow_headers=["Authorization", "X-API-Key", "Content-Type", "X-CSRF-Token"])
app.include_router(router)
app.include_router(sessions_router)
app.include_router(onboarding_router)


@app.get("/healthz")
async def health():
    return {"ok": True, "service": "traceverdict-cases"}


@app.get("/readyz")
async def ready(request: Request):
    healthy = request.app.state.engine.store.ping()
    return JSONResponse({"ready": healthy, "database": healthy}, status_code=200 if healthy else 503)


@app.get("/v1/agents")
async def agents(request: Request, p: Principal = require("project")):
    return {"agents": [{"agent_id": name, "tenant_id": request.app.state.engine.policy_loader(name).org}
                       for name in request.app.state.engine.list_agents() if can_see(request, p, name)]}


@app.get("/v1/connections")
async def connections(request: Request, p: Principal = require("project")):
    svc = request.app.state.cases
    result = {"database": {"online": svc.engine.store.ping()}}
    try:
        routes = await svc.models.discover()
        result["nightshift"] = {"online": True, "discovered_model_count": len(routes),
                                "requested_model": os.environ.get("METERLESS_MODEL"),
                                "requested_replay_model": os.environ.get("METERLESS_REPLAY_MODEL") or os.environ.get("METERLESS_MODEL")}
    except Exception:
        result["nightshift"] = {"online": False}
    # Probe the view's real SQL contract, not a cached sample.
    view = os.environ.get("ZETARIS_CASE_VIEW", "traceverdict.case_evidence")
    if not __import__("re").fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", view):
        result["zetaris"] = {"online": False}
        return result
    try:
        import uuid
        rid = str(uuid.uuid4())
        response = await svc.client.post(os.environ["ZETARIS_REST_URL"].rstrip("/") + "/sql-editor/sqls/run",
            headers={"Authorization": "Bearer " + os.environ["ZETARIS_API_KEY"],
                     "X-Org-ID": os.environ["ZETARIS_ORG_ID"], "X-Request-ID": rid},
            json={"queryId": rid, "sql": f"SELECT evidence_kind FROM {view} LIMIT 1", "source": "SqlEditor", "limit": 1}, timeout=15)
        result["zetaris"] = {"online": response.status_code == 200, "view": view}
    except Exception:
        result["zetaris"] = {"online": False, "view": view}
    return result
