"""Credential-free sponsor sample API. Only TraceVerdict routes are exposed.

Local API authentication still uses INTENTSEAL_API_KEYS. This app is not the
production enforcement gateway and never exposes inspection/proxy endpoints.
"""
import asyncio
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from intentseal_core.config import load_env
from intentseal_core.decision_model import StaticDecisionModel
from intentseal_core.engine import Engine
from intentseal_core.policy import AgentPolicy
from intentseal_core.store import Store
from ..security import BodySizeLimit, KeyRing
from .api import router
from .service import CaseService


class SampleScorer:
    def score(self, text):
        return 0.0


def policy(agent):
    if agent != "research-agent":
        raise ValueError("sample agent not configured")
    return AgentPolicy(agent=agent)


@asynccontextmanager
async def lifespan(app):
    load_env()
    app.state.sample_only = True
    app.state.keys = KeyRing()
    app.state.engine = Engine(store=Store(os.environ.get("TRACEVERDICT_SAMPLE_DB", "data/traceverdict-sample.db")),
                              policy_loader=policy, decision_model=StaticDecisionModel(0), classifiers=[SampleScorer()])
    app.state.cases = CaseService(app.state.engine)
    recovery = asyncio.create_task(app.state.cases.recover())
    try:
        yield
    finally:
        recovery.cancel()
        await asyncio.gather(recovery, return_exceptions=True)
        await app.state.cases.close()


app = FastAPI(title="TraceVerdict sample backend", version="0.1.0", lifespan=lifespan,
              description="Synthetic, deterministic sample cases only. No live sponsor inference or production enforcement.")
app.add_middleware(BodySizeLimit)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in os.environ.get(
    "INTENTSEAL_CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()],
    allow_methods=["GET", "POST"], allow_headers=["Authorization", "X-API-Key", "Content-Type"])
app.include_router(router)
