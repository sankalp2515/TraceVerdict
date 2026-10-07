"""LLM Proxy (PRX-1…PRX-5): OpenAI-compatible /proxy/v1/chat/completions.

An unmodified agent changes only its base URL. The agent is named in the URL
(`/proxy/<agent_id>/v1`, so OPENAI_BASE_URL alone is enough) or by the X-Agent-Id header; the session comes from
X-Session-Id or, for clients that send neither, from a fingerprint of the conversation's opening messages
(PRX-5). The proxy inspects user and tool messages before forwarding (PRX-2) - each message once per session;
its decision, including neutralised text, is re-applied when the client resends the history - forwards through
the router to free upstream providers (PRX-4), and checks every tool call the model returns (PRX-3): blocked
calls are removed and replaced by a notice; pinned fields are rewritten. System messages are trusted.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from collections import OrderedDict
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from intentseal_core.llm.adapters import ChatRequest
from intentseal_core.llm.router import AllProvidersFailed
from intentseal_core.types import Decision

from .security import Principal, require
from .tenancy import require_agent

router = APIRouter(tags=["proxy"])
PROXY_ROLE = "proxy_upstream"


def _text(content: Any) -> str:
    if isinstance(content, list):   # OpenAI content parts
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return content or ""


_SEEN_MAX = 2000   # sessions whose per-message decisions are kept in memory


def _seen(request: Request) -> OrderedDict[str, dict[str, tuple[str, dict[str, Any] | None]]]:
    state = request.app.state
    if not hasattr(state, "proxy_seen"):
        state.proxy_seen = OrderedDict()
    return state.proxy_seen


def _conversation_id(agent_id: str, messages: list[dict[str, Any]]) -> str:
    """Stable id for clients that send no session header: the system prompt + first user message."""
    opening = [(m.get("role"), _text(m.get("content"))) for m in messages if m.get("role") in ("system", "user")][:2]
    return "conv-" + hashlib.sha256(json.dumps([agent_id, opening]).encode()).hexdigest()[:16]


@router.post("/proxy/v1/chat/completions")
async def chat_completions(request: Request, p: Principal = require("project")) -> Any:
    return await _complete(request, request.headers.get("x-agent-id", "default-agent"), p)


@router.post("/proxy/{agent_id}/v1/chat/completions")
async def agent_chat_completions(agent_id: str, request: Request, p: Principal = require("project")) -> Any:
    return await _complete(request, agent_id, p)


async def _complete(request: Request, agent_id: str, p: Principal) -> Any:
    require_agent(request, p, agent_id)
    try:
        body = await request.json()
    except ValueError:
        body = None
    if not isinstance(body, dict) or not isinstance(body.get("messages", []), list)             or not all(isinstance(m, dict) for m in body.get("messages", [])):
        return JSONResponse({"error": {"message": "body must be a chat completion request with a messages list",
                                       "type": "invalid_request_error"}}, status_code=422)
    engine = request.app.state.engine
    messages: list[dict[str, Any]] = [dict(m) for m in body.get("messages", [])]
    session_id = request.headers.get("x-session-id") or _conversation_id(agent_id, messages)
    if session_id not in engine.sessions:
        first_user = next((_text(m.get("content")) for m in messages if m.get("role") == "user"), "")
        engine.start_session(agent_id, task=first_user, session_id=session_id)
    seen = _seen(request).setdefault(session_id, {})
    _seen(request).move_to_end(session_id)
    while len(_seen(request)) > _SEEN_MAX:
        _seen(request).popitem(last=False)

    # PRX-2: inspect user and tool messages (each once per session); tool_call ids give the source label.
    call_names: dict[str, str] = {}
    findings_summary: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        for tc in m.get("tool_calls") or []:
            call_names[tc.get("id", "")] = (tc.get("function") or {}).get("name", "tool")
        if role not in ("user", "tool"):
            continue
        source = "user" if role == "user" else f"tool:{call_names.get(m.get('tool_call_id', ''), 'tool')}"
        text = _text(m.get("content"))
        if not text:
            continue
        key = hashlib.sha256(f"{source}\n{text}".encode()).hexdigest()
        if key not in seen:
            r = await engine.inspect(text, source, agent_id, session_id=session_id)
            if r.enforced == Decision.ALLOW:
                seen[key] = (text, None)
            else:
                replacement = (r.cleaned_content if r.enforced == Decision.NEUTRALISE
                               else f"[Content withheld by the security policy: {r.reason}]")
                seen[key] = (replacement, {"source": source, "decision": r.enforced.value, "rule": r.policy_rule,
                                           "labels": r.labels, "event_id": r.event_id})
        replacement, finding = seen[key]
        if finding is not None:
            findings_summary.append(finding)
            m["content"] = replacement

    req = ChatRequest(messages=messages, tools=body.get("tools"), tool_choice=body.get("tool_choice"),
                      temperature=body.get("temperature", 0), max_tokens=body.get("max_tokens") or 1024)
    security = {"session_id": session_id, "inbound": findings_summary}
    if body.get("stream"):
        try:
            upstream = await engine.router.stream_chat(PROXY_ROLE, req)
        except AllProvidersFailed as e:
            return _unavailable(e)
        include_usage = bool((body.get("stream_options") or {}).get("include_usage"))
        return StreamingResponse(_stream(engine, upstream, agent_id, session_id, security, include_usage),
                                 media_type="text/event-stream")
    try:
        res = await engine.router.chat(PROXY_ROLE, req)
    except AllProvidersFailed as e:
        return _unavailable(e)

    kept, notices = await _check_tool_calls(engine, res.tool_calls, agent_id, session_id)
    content = res.content or ""
    if notices:
        content = (content + "\n\n" if content else "") + "\n".join(notices)
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if kept:
        message["tool_calls"] = kept
    return {
        "id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion", "created": int(time.time()),
        "model": f"{res.provider}/{res.model}",
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if kept else "stop"}],
        "usage": {"prompt_tokens": res.input_tokens, "completion_tokens": res.output_tokens,
                  "total_tokens": res.input_tokens + res.output_tokens},
        "x_security": {**security, "blocked_tool_calls": len(notices)},
    }


def _unavailable(e: Exception) -> JSONResponse:
    return JSONResponse({"error": {"message": "all upstream providers unavailable", "type": "upstream_unavailable",
                                   "detail": str(e)[:300]}}, status_code=503)


async def _check_tool_calls(engine: Any, tool_calls: list[dict[str, Any]], agent_id: str,
                            session_id: str) -> tuple[list[dict[str, Any]], list[str]]:
    """PRX-3: check each tool call before the agent can run it. Blocked calls become notices; pinned fields are
    rewritten in the released call."""
    kept, notices = [], []
    for tc in tool_calls:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_raw": fn.get("arguments")}
        if not isinstance(args, dict):
            args = {"_raw": fn.get("arguments")}
        ar = await engine.check_action(fn.get("name", ""), args, agent_id, session_id=session_id)
        if ar.enforced == Decision.ALLOW:
            if ar.pinned_overrides:
                tc = {**tc, "function": {**fn, "arguments": json.dumps(ar.final_args)}}
            kept.append(tc)
        else:
            notices.append(ar.notice or f"Tool call '{fn.get('name')}' was blocked by the security policy.")
    return kept, notices


def _sse(obj: Any) -> str:
    return f"data: {json.dumps(obj)}\n\n"


async def _stream(engine: Any, upstream: Any, agent_id: str, session_id: str, security: dict[str, Any],
                  include_usage: bool):
    """PRX-6: text deltas stream through as they arrive; tool-call deltas are buffered until the upstream stream
    ends, assembled, checked, and only then released (allowed calls) or replaced by a notice (blocked calls).
    If the upstream fails part-way, buffered tool calls are never released."""
    cid, created = "chatcmpl-" + uuid.uuid4().hex[:24], int(time.time())
    model = f"{upstream.provider}/{upstream.model}"

    def chunk(delta: dict[str, Any], finish: str | None = None, **extra: Any) -> str:
        return _sse({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model,
                     "choices": [{"index": 0, "delta": delta, "finish_reason": finish}], **extra})

    calls: dict[int, dict[str, Any]] = {}
    finish, started = None, False
    try:
        async for c in upstream.chunks():
            for choice in c.get("choices") or []:
                delta = choice.get("delta") or {}
                for pos, tc in enumerate(delta.get("tool_calls") or []):
                    i = tc.get("index", pos)
                    slot = calls.setdefault(i, {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    slot["id"] = tc.get("id") or slot["id"]
                    fn = tc.get("function") or {}
                    slot["function"]["name"] += fn.get("name") or ""
                    slot["function"]["arguments"] += fn.get("arguments") or ""
                if delta.get("content"):
                    yield chunk({**({} if started else {"role": "assistant"}), "content": delta["content"]})
                    started = True
                finish = choice.get("finish_reason") or finish
    except Exception as e:   # upstream failed mid-stream: say so; buffered tool calls are dropped, never released
        yield _sse({"error": {"message": "upstream stream failed", "type": "upstream_error", "detail": type(e).__name__}})
        yield "data: [DONE]\n\n"
        return
    ordered = [calls[i] for i in sorted(calls)]
    for tc in ordered:
        tc["id"] = tc["id"] or f"call_{uuid.uuid4().hex[:12]}"
    kept, notices = await _check_tool_calls(engine, ordered, agent_id, session_id)
    if notices:
        text = ("\n\n" if started else "") + "\n".join(notices)
        yield chunk({**({} if started else {"role": "assistant"}), "content": text})
        started = True
    if kept:
        yield chunk({**({} if started else {"role": "assistant"}),
                     "tool_calls": [{**tc, "index": i} for i, tc in enumerate(kept)]})
    final = "tool_calls" if kept else ("stop" if finish in (None, "tool_calls") else finish)
    yield chunk({}, final, x_security={**security, "blocked_tool_calls": len(notices)})
    if include_usage:
        h = upstream.handle
        yield _sse({"id": cid, "object": "chat.completion.chunk", "created": created, "model": model, "choices": [],
                    "usage": {"prompt_tokens": h.input_tokens, "completion_tokens": h.output_tokens,
                              "total_tokens": h.input_tokens + h.output_tokens}})
    yield "data: [DONE]\n\n"
