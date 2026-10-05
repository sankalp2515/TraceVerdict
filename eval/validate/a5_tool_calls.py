"""Validate A5: can we parse tool calls from each free provider's OpenAI-compatible endpoint,
and does a full tool round trip (assistant tool_call -> tool result -> final answer) work?

Usage: python eval/validate/a5_tool_calls.py  -> writes eval/validate/results/a5.json
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from asg_core.llm.adapters import ChatRequest, ProviderError
from asg_core.llm.router import Router

logging.getLogger("httpx").setLevel(logging.WARNING)

CANDIDATES = [
    ("groq", "openai/gpt-oss-120b"), ("groq", "openai/gpt-oss-20b"), ("groq", "qwen/qwen3.8-27b"),
    ("gemini", "gemini-3.5-flash"), ("gemini", "gemini-flash-latest"), ("gemini", "gemini-3.1-flash-lite"),
    ("nvidia", "openai/gpt-oss-20b"), ("nvidia", "nvidia/nemotron-3-super-120b-a12b"),
    ("openrouter", "qwen/qwen3.8-27b:free"), ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
]

TOOLS = [{
    "type": "function",
    "function": {
        "name": "query_db",
        "description": "Look up a customer record by customer_id.",
        "parameters": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                       "required": ["customer_id"]},
    },
}]


async def check(router: Router, prov: str, model: str) -> dict:
    out: dict = {"provider": prov, "model": model}
    msgs = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed."},
        {"role": "user", "content": "What city is customer C-1042 in? Use the database."},
    ]
    try:
        r1 = await router.call_direct(prov, model, ChatRequest(messages=msgs, tools=TOOLS, max_tokens=800), role="validate")
    except ProviderError as e:
        return {**out, "ok": False, "stage": "call1", "error": e.kind}
    out["latency_ms_1"] = round(r1.latency_ms)
    if not r1.tool_calls:
        return {**out, "ok": False, "stage": "no_tool_call", "content": (r1.content or "")[:120]}
    tc = r1.tool_calls[0]
    try:
        args = json.loads(tc["function"]["arguments"] or "{}")
        well_formed = bool(tc.get("id")) and tc["function"]["name"] == "query_db" and "customer_id" in args
    except (KeyError, json.JSONDecodeError, TypeError):
        well_formed, args = False, None
    out.update(tool_call_well_formed=well_formed, args=args)
    msgs2 = msgs + [
        {"role": "assistant", "content": r1.content or "", "tool_calls": r1.tool_calls},
        {"role": "tool", "tool_call_id": tc.get("id", "call_0"), "content": json.dumps({"customer_id": "C-1042", "city": "Pune"})},
    ]
    try:
        r2 = await router.call_direct(prov, model, ChatRequest(messages=msgs2, tools=TOOLS, max_tokens=800), role="validate")
    except ProviderError as e:
        return {**out, "ok": False, "stage": "call2", "error": e.kind}
    out["latency_ms_2"] = round(r2.latency_ms)
    out["round_trip_answer_correct"] = "pune" in (r2.content or "").lower()
    out["ok"] = well_formed and out["round_trip_answer_correct"]
    return out


async def main() -> None:
    router = Router()
    results = []
    for prov, model in CANDIDATES:
        res = await check(router, prov, model)
        print(json.dumps(res))
        results.append(res)
    await router.aclose()
    path = Path(__file__).parent / "results" / "a5.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
