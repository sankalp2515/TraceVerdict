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
    return await _complete(request, request.headers.get("x-agent-id", "default-agent"))


@router.post("/proxy/{agent_id}/v1/chat/completions")
async def agent_chat_completions(agent_id: str, request: Request, p: Principal = require("project")) -> Any:
    return await _complete(request, agent_id)


async def _complete(request: Request, agent_id: str) -> Any:
    body = await request.json()
    engine = request.app.state.engine
    messages: list[dict[str, Any]] = [dict(m) for m in body.get("messages", [])]
    session_id = request.headers.get("x-session-id") or _conversation_id(agent_id, messages)
    if session_id not in getattr(engine.sessions, "_s", {}):
        first_user = next((_text(m.get("content")) for m in messages if m.get("role") == "user"), "")
        s = engine.start_session(agent_id, task=first_user)
        engine.sessions._s.pop(s.session_id, None)
        s.session_id = session_id
        engine.sessions._s[session_id] = s
        engine.logger.session(session_id, agent_id, s.user_ref, first_user)
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
    try:
        res = await engine.router.chat(PROXY_ROLE, req)
    except AllProvidersFailed as e:
        return JSONResponse({"error": {"message": "all upstream providers unavailable", "type": "upstream_unavailable",
                                       "detail": str(e)[:300]}}, status_code=503)

    # PRX-3: check each tool call before the agent can run it.
    kept, notices = [], []
    for tc in res.tool_calls:
        fn = tc.get("function") or {}
        try:
            args = json.loads(fn.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {"_raw": fn.get("arguments")}
        ar = await engine.check_action(fn.get("name", ""), args, agent_id, session_id=session_id)
        if ar.enforced == Decision.ALLOW:
            if ar.pinned_overrides:
                tc = {**tc, "function": {**fn, "arguments": json.dumps(ar.final_args)}}
            kept.append(tc)
        else:
            notices.append(ar.notice or f"Tool call '{fn.get('name')}' was blocked by the security policy.")
    content = res.content or ""
    if notices:
        content = (content + "\n\n" if content else "") + "\n".join(notices)
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if kept:
        message["tool_calls"] = kept
    completion = {
        "id": "chatcmpl-" + uuid.uuid4().hex[:24], "object": "chat.completion", "created": int(time.time()),
        "model": f"{res.provider}/{res.model}",
        "choices": [{"index": 0, "message": message, "finish_reason": "tool_calls" if kept else "stop"}],
        "usage": {"prompt_tokens": res.input_tokens, "completion_tokens": res.output_tokens,
                  "total_tokens": res.input_tokens + res.output_tokens},
        "x_security": {"session_id": session_id, "inbound": findings_summary, "blocked_tool_calls": len(notices)},
    }
    if body.get("stream"):
        return StreamingResponse(_as_stream(completion), media_type="text/event-stream")
    return completion


async def _as_stream(c: dict[str, Any]):
    """Minimal streaming compatibility: the checked message is sent as one chunk (PRX-6 is P1)."""
    msg = c["choices"][0]["message"]
    delta: dict[str, Any] = {"role": "assistant", "content": msg.get("content", "")}
    if msg.get("tool_calls"):
        delta["tool_calls"] = [{**tc, "index": i} for i, tc in enumerate(msg["tool_calls"])]
    chunk = {"id": c["id"], "object": "chat.completion.chunk", "created": c["created"], "model": c["model"],
             "choices": [{"index": 0, "delta": delta, "finish_reason": c["choices"][0]["finish_reason"]}]}
    yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"
