"""SQLite persistence (MVP; schema kept portable to Postgres).

This module owns LLM usage and the response cache. Decision/event tables are added by the
decision logger (CORE-10) through `Store.ensure_schema`.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

from .secrets import redact

_SCHEMA = [
    """CREATE TABLE IF NOT EXISTS llm_usage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        role TEXT, provider TEXT, key_alias TEXT, model TEXT,
        status TEXT NOT NULL,            -- ok | rate_limited | auth_failed | server_error | timeout | bad_request | not_found | error | cached
        http_status INTEGER,
        latency_ms REAL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        est_cost_usd REAL DEFAULT 0,
        cached INTEGER DEFAULT 0,
        error TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS ix_llm_usage_ts ON llm_usage(ts)",
    "CREATE INDEX IF NOT EXISTS ix_llm_usage_provider ON llm_usage(provider, ts)",
    """CREATE TABLE IF NOT EXISTS llm_cache (
        cache_key TEXT PRIMARY KEY,
        payload TEXT NOT NULL,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL
    )""",
]


class Store:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(path), check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.row_factory = sqlite3.Row
        self.ensure_schema(_SCHEMA)

    def ensure_schema(self, statements: list[str]) -> None:
        with self._lock:
            for s in statements:
                self._conn.execute(s)

    def execute(self, sql: str, params: tuple | dict = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    # ---- LLM usage -------------------------------------------------------------------------
    def record_usage(self, **row: Any) -> None:
        if row.get("error"):
            row["error"] = redact(str(row["error"]))[:500]
        row.setdefault("ts", time.time())
        cols = ", ".join(row)
        marks = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO llm_usage ({cols}) VALUES ({marks})", row)

    def tokens_today(self, provider: str) -> int:
        start = time.time() - (time.time() % 86400)  # UTC day
        r = self.query(
            "SELECT COALESCE(SUM(input_tokens + output_tokens), 0) AS t FROM llm_usage "
            "WHERE provider = ? AND ts >= ? AND cached = 0",
            (provider, start),
        )
        return int(r[0]["t"])

    # ---- Response cache --------------------------------------------------------------------
    def cache_get(self, key: str) -> dict[str, Any] | None:
        r = self.query("SELECT payload, expires_at FROM llm_cache WHERE cache_key = ?", (key,))
        if not r or r[0]["expires_at"] < time.time():
            return None
        return json.loads(r[0]["payload"])

    def cache_put(self, key: str, payload: dict[str, Any], ttl_s: int) -> None:
        now = time.time()
        self.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, payload, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (key, json.dumps(payload), now, now + ttl_s),
        )
