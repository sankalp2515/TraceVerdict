"""Explicit live sponsor adapters. Missing credentials never select the sample backend."""
from __future__ import annotations

import json
import asyncio
import os
import re
import time
import uuid
from pathlib import Path

import httpx

from intentseal_core.config import ProviderConfig
from intentseal_core.llm.adapters import ChatRequest, OpenAICompatibleAdapter, ProviderError
from intentseal_core.secrets import ApiKey, registry

from .models import Evidence, digest


class IntegrationUnavailable(RuntimeError):
    pass


def runtime_profile() -> dict:
    primary = os.getenv("METERLESS_MODEL", "")
    return {"primary_route": primary, "replay_route": os.getenv("METERLESS_REPLAY_MODEL") or primary,
            "reasoning": os.getenv("METERLESS_REASONING", "false").lower() == "true",
            "endpoint_sha256": digest(os.getenv("METERLESS_BASE_URL", "")),
            "adapter_sha256": digest(Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n"))}


class Nightshift:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    def configuration(self) -> tuple[ProviderConfig, ApiKey, str]:
        url, token, route = (os.getenv(k, "") for k in ("METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL"))
        if not all((url, token, route)):
            raise IntegrationUnavailable("Nightshift Runtime URL, token and discovered route are required")
        registry.register(token)
        key = ApiKey("nightshift-runtime", token)
        provider = ProviderConfig("nightshift", "openai_compatible", True, url.rstrip("/"), [key],
                                  timeout_s=min(180, max(10, float(os.getenv("METERLESS_TIMEOUT_S", "75")))),
                                  extra_headers={"meterless-app": "traceverdict", "meterless-scope": "user"})
        return provider, key, route

    async def discover(self) -> list:
        provider, key, _ = self.configuration()
        r = await self.client.get(provider.base_url + "/models", headers={"Authorization": f"Bearer {key.value}",
                                  **provider.extra_headers}, timeout=15)
        if r.status_code != 200:
            raise IntegrationUnavailable("Nightshift model discovery failed")
        return r.json().get("data", [])

    async def call(self, role: str, messages: list[dict], tools: list[dict] | None = None) -> tuple[dict, dict]:
        provider, key, route = self.configuration()
        if role == "replay-agent":
            route = os.getenv("METERLESS_REPLAY_MODEL") or route
        start = time.perf_counter()
        token_limit = {"investigator": 2500, "critic": 2500, "repair": 2500, "replay-agent": 1500}.get(role, 2500)
        # NVIDIA documents this option for Lightning. Bounded structured tasks do
        # not need a private thinking stream that can consume the entire token cap.
        extra = ({"chat_template_kwargs": {"enable_thinking": os.getenv("METERLESS_REASONING", "false").lower() == "true"}}
                 if "nemotron-3.5-lightning" in route else {})
        attempts = []
        choice = ({"type": "function", "function": {"name": tools[0]["function"]["name"]}}
                  if tools and len(tools) == 1 else None)
        for attempt in range(2):
            attempt_start = time.perf_counter()
            try:
                result = await OpenAICompatibleAdapter().chat(provider, key, route,
                            ChatRequest(messages=messages, tools=tools, tool_choice=choice, max_tokens=token_limit, extra=extra), self.client)
                attempts.append({"status": "complete", "duration_ms": round((time.perf_counter() - attempt_start) * 1000)})
                break
            except ProviderError as exc:
                attempts.append({"status": "failed", "kind": exc.kind, "http_status": exc.http_status,
                                 "duration_ms": round((time.perf_counter() - attempt_start) * 1000)})
                if attempt or exc.kind not in ("server_error", "rate_limited", "timeout"):
                    raise
                await asyncio.sleep(min(3, max(.5, exc.retry_after_s or 1)))
        # Only explicitly returned attribution is recorded, not inferred from a route name.
        receipt = {"role": role, "execution_mode": "live", "requested_route": route,
                   "response_id": result.raw.get("id"), "actual_model_evidence": result.raw.get("model"),
                   "provider_evidence": result.raw.get("provider"),
                   "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
                   "attempts": attempts,
                   "requested_generation_options": extra,
                   "duration_ms": round((time.perf_counter() - start) * 1000, 3)}
        return {"content": result.content, "tool_calls": result.tool_calls}, receipt


class Zetaris:
    # A governed view must join event evidence, historical configuration and trusted reference data.
    # The deployment script documents this contract; SELECT-only templates never accept model SQL.
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def read(self, case: dict, kind: str | None = None) -> list[Evidence]:
        url, token, org = (os.getenv(k, "") for k in ("ZETARIS_REST_URL", "ZETARIS_API_KEY", "ZETARIS_ORG_ID"))
        if not all((url, token, org)):
            raise IntegrationUnavailable("Zetaris REST URL, API credential and organization ID are required")
        registry.register(token)
        def literal(value: str) -> str:
            return "'" + value.replace("'", "''") + "'"
        view = os.getenv("ZETARIS_CASE_VIEW", "traceverdict.case_evidence")
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", view):
            raise ValueError("invalid governed view name")
        sql = (f"SELECT evidence_json FROM {view} WHERE tenant_id={literal(case['tenant_id'])} "
               f"AND agent_id={literal(case['agent_id'])} AND case_id={literal(case['case_id'])}")
        if kind:
            if kind not in ("task", "document", "action", "receipt", "policy", "tools", "reference", "event"):
                raise ValueError("unsupported evidence kind")
            sql += " AND evidence_kind=" + literal(kind)
        sql += " LIMIT 100"
        rid = str(uuid.uuid4())
        response = await self.client.post(url.rstrip("/") + "/sql-editor/sqls/run",
                    headers={"Authorization": f"Bearer {token}", "X-Org-ID": org, "X-Request-ID": rid},
                    json={"queryId": rid, "sql": sql, "source": "SqlEditor", "limit": 100}, timeout=25)
        if response.status_code != 200:
            raise IntegrationUnavailable("Zetaris evidence query failed")
        data = response.json()
        # Official getting-started RestChannel returns column arrays under `data`.
        # A named `rows` projection is also accepted for a governed API wrapper.
        rows = data.get("data", data.get("rows")) if isinstance(data, dict) else None
        if not isinstance(rows, list) or len(rows) > 100:
            raise IntegrationUnavailable("Zetaris response has no supported evidence rows")
        output = []
        for row in rows:
            if isinstance(row, list) and len(row) == 1:
                raw = row[0]
            elif isinstance(row, dict) and set(row) == {"evidence_json"}:
                raw = row["evidence_json"]
            else:
                raise IntegrationUnavailable("unsupported evidence row shape")
            record = Evidence.model_validate(json.loads(raw) if isinstance(raw, str) else raw)
            if (record.tenant_id, record.agent_id, record.case_id) != (case["tenant_id"], case["agent_id"], case["case_id"]):
                raise ValueError("Zetaris returned out-of-scope evidence")
            if digest(record.payload) != record.content_sha256:
                raise ValueError("Zetaris evidence hash mismatch")
            output.append(record.model_copy(update={"query_receipt": {"request_id": rid, "query_sha256": digest(sql),
                                          "response_sha256": digest(data), "execution_mode": "live"}}))
        return output
