"""Revocable browser sessions backed by the case database; API keys stay server-side."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, SecretStr

from ..security import Principal

COOKIE = "traceverdict_session"
router = APIRouter(tags=["Workspace sessions"])


def fingerprint(value):
    return hashlib.sha256(value.encode()).hexdigest()


class SessionStore:
    def __init__(self, store, keys, origins):
        self.store, self.keys, self.origins = store, keys, set(origins)
        store.ensure_schema(["CREATE TABLE IF NOT EXISTS tv_browser_sessions (token_sha256 TEXT PRIMARY KEY,"
                             "credential_sha256 TEXT NOT NULL,csrf TEXT NOT NULL,expires_at REAL NOT NULL)",
                             "CREATE INDEX IF NOT EXISTS tv_browser_expiry ON tv_browser_sessions(expires_at)"])

    def lookup(self, token):
        if not token:
            return None
        rows = self.store.query("SELECT credential_sha256,csrf,expires_at FROM tv_browser_sessions WHERE token_sha256=? AND expires_at>?",
                                (fingerprint(token), time.time()))
        if not rows:
            return None
        row = rows[0]
        principal = self.keys.lookup_fingerprint(row["credential_sha256"])
        return (principal, row) if principal else None

    def authenticate(self, request):
        found = self.lookup(request.cookies.get(COOKIE))
        if not found:
            return None
        principal, row = found
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("origin") not in self.origins:
                raise HTTPException(403, "workspace origin is not allowed")
            if not hmac.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf"]):
                raise HTTPException(403, "missing or invalid CSRF token")
        return principal


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_key: SecretStr


def identity(principal, row):
    return {"name": principal.name, "scope": principal.scope, "org": principal.org,
            "csrf_token": row["csrf"], "expires_at": row["expires_at"]}


@router.post("/v1/auth/session")
async def login(body: Login, request: Request, response: Response):
    state = request.app.state
    if request.headers.get("origin") and request.headers["origin"] not in state.sessions.origins:
        raise HTTPException(403, "workspace origin is not allowed")
    client = request.client.host if request.client else "unknown"
    if not state.keys.allow(Principal("workspace-login", "public"), client):
        raise HTTPException(429, "login rate limit exceeded", headers={"Retry-After": "60"})
    key = body.api_key.get_secret_value()
    principal = state.keys.lookup(key)
    if not principal or principal.scope not in ("project", "admin"):
        raise HTTPException(401, "invalid workspace credential")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires = time.time() + 8 * 3600
    state.engine.store.execute("DELETE FROM tv_browser_sessions WHERE expires_at<=?", (time.time(),))
    state.engine.store.execute("INSERT INTO tv_browser_sessions VALUES(?,?,?,?)",
                               (fingerprint(token), fingerprint(key), csrf, expires))
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=os.environ.get(
        "TRACEVERDICT_COOKIE_SECURE", "true").lower() == "true", max_age=8 * 3600, path="/")
    response.headers["Cache-Control"] = "no-store"
    return identity(principal, {"csrf": csrf, "expires_at": expires})


@router.get("/v1/auth/session")
async def current(request: Request, response: Response):
    found = request.app.state.sessions.lookup(request.cookies.get(COOKIE))
    if not found:
        raise HTTPException(401, "workspace session expired")
    response.headers["Cache-Control"] = "no-store"
    return identity(*found)


@router.post("/v1/auth/logout")
async def logout(request: Request, response: Response):
    if not request.app.state.sessions.authenticate(request):
        raise HTTPException(401, "workspace session expired")
    request.app.state.engine.store.execute("DELETE FROM tv_browser_sessions WHERE token_sha256=?",
        (fingerprint(request.cookies[COOKIE]),))
    response.delete_cookie(COOKIE, path="/")
    return {"signed_out": True}
