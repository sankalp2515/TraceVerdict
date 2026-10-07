"""Gateway self-security (API-8, API-9, NFR §12): API keys (hashed at rest), scopes, rate limits,
request-size limits. Keys come from the environment only.

INTENTSEAL_API_KEYS     comma list of name:key:scope  (scope: admin | project), e.g. "dev:abc123:admin"
INTENTSEAL_PUBLIC_KEY   optional read-only key for the public Console (scope: public)
INTENTSEAL_RATE_LIMIT_PER_MIN / INTENTSEAL_PUBLIC_RATE_LIMIT_PER_MIN   requests per minute per key
INTENTSEAL_MAX_BODY_BYTES   max request body (default 2 MB)
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from starlette.responses import JSONResponse

SCOPES = {"public": 0, "project": 1, "admin": 2}


@dataclass(frozen=True)
class Principal:
    name: str
    scope: str


def _h(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


class KeyRing:
    def __init__(self) -> None:
        self._keys: dict[str, Principal] = {}
        for item in filter(None, (s.strip() for s in os.environ.get("INTENTSEAL_API_KEYS", "").split(","))):
            parts = item.split(":")
            if len(parts) == 3 and parts[2] in SCOPES:
                self._keys[_h(parts[1])] = Principal(parts[0], parts[2])
        pub = os.environ.get("INTENTSEAL_PUBLIC_KEY")
        if pub:
            self._keys[_h(pub)] = Principal("public", "public")
        self._buckets: dict[str, list[float]] = {}
        self.limit = int(os.environ.get("INTENTSEAL_RATE_LIMIT_PER_MIN") or "120")
        self.public_limit = int(os.environ.get("INTENTSEAL_PUBLIC_RATE_LIMIT_PER_MIN") or "20")

    def add(self, key: str, principal: Principal) -> None:
        """Register an in-process key (e.g. the demo runner's ephemeral key for calling its own proxy)."""
        self._keys[_h(key)] = principal

    def lookup(self, key: str | None) -> Principal | None:
        if not key:
            return None
        h = _h(key)
        for stored, p in self._keys.items():
            if hmac.compare_digest(stored, h):
                return p
        return None

    def allow(self, p: Principal) -> bool:
        now = time.time()
        bucket = [t for t in self._buckets.get(p.name, []) if now - t < 60]
        limit = self.public_limit if p.scope == "public" else self.limit
        if len(bucket) >= limit:
            self._buckets[p.name] = bucket
            return False
        bucket.append(now)
        self._buckets[p.name] = bucket
        return True


def _key_from(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key")


def require(scope: str):
    async def dep(request: Request) -> Principal:
        ring: KeyRing = request.app.state.keys
        p = ring.lookup(_key_from(request))
        if p is None:
            raise HTTPException(401, "missing or invalid API key")
        if SCOPES[p.scope] < SCOPES[scope]:
            raise HTTPException(403, f"this key cannot access {scope}-scoped endpoints")
        if not ring.allow(p):
            raise HTTPException(429, "rate limit exceeded", headers={"Retry-After": "60"})
        return p

    return Depends(dep)


class BodySizeLimit:
    """Reject bodies over the limit without buffering them: a declared Content-Length is checked up front, and a
    chunked body is counted as it streams in (413 as soon as it passes the limit). Runs before authentication."""

    def __init__(self, app, max_bytes: int | None = None) -> None:
        self.app = app
        self.max = max_bytes or int(os.environ.get("INTENTSEAL_MAX_BODY_BYTES") or 2 * 1024 * 1024)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        cl = dict(scope.get("headers") or []).get(b"content-length", b"").decode("latin-1")
        if cl.isdigit() and int(cl) > self.max:
            return await JSONResponse({"detail": "request body too large"}, status_code=413)(scope, receive, send)
        seen = 0

        async def limited_receive():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.max:
                    raise HTTPException(413, "request body too large")
            return message

        await self.app(scope, limited_receive, send)
