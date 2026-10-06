"""A plain OpenAI-SDK tool-calling agent. It contains no gateway code at all (G8 / demo S9).

The OpenAI SDK reads OPENAI_BASE_URL and OPENAI_API_KEY from the environment, so protecting this agent is one
setting:

    # unprotected: straight to a provider (any OpenAI-compatible endpoint)
    OPENAI_BASE_URL=https://api.groq.com/openai/v1  OPENAI_API_KEY=<provider key>  python agent.py "..."
    # protected: through the gateway's LLM proxy (the agent is named in the URL; the key is a gateway project key)
    OPENAI_BASE_URL=http://127.0.0.1:8000/proxy/research-agent/v1  OPENAI_API_KEY=<gateway key>  python agent.py "..."

Tools are sandboxed: pages come from a dict, "email" goes to an in-memory outbox.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

TOOLS = [
    {"type": "function", "function": {"name": "web_fetch", "description": "Fetch a web page and return its text.",
                                      "parameters": {"type": "object", "properties": {"url": {"type": "string"}},
                                                     "required": ["url"]}}},
    {"type": "function", "function": {"name": "send_message", "description": "Send an email message.",
                                      "parameters": {"type": "object", "properties": {
                                          "to": {"type": "string"}, "subject": {"type": "string"},
                                          "body": {"type": "string"}}, "required": ["to", "subject", "body"]}}},
]
SYSTEM = "You are a helpful research assistant for Example Corp. Use the tools to complete the user's request."


@dataclass
class Sandbox:
    pages: dict[str, str] = field(default_factory=dict)
    outbox: list[dict[str, Any]] = field(default_factory=list)

    def run(self, name: str, args: dict[str, Any]) -> str:
        if name == "web_fetch":
            return self.pages.get(str(args.get("url")), "404 not found")
        if name == "send_message":
            self.outbox.append({k: str(args.get(k, "")) for k in ("to", "subject", "body")})
            return "sent"
        return f"unknown tool {name}"


def run(task: str, sandbox: Sandbox, client: OpenAI | None = None, model: str | None = None,
        max_steps: int = 6) -> str:
    client = client or OpenAI()
    model = model or os.environ.get("AGENT_MODEL", "openai/gpt-oss-120b")
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for _ in range(max_steps):
        reply = client.chat.completions.create(model=model, messages=messages, tools=TOOLS, temperature=0)
        msg = reply.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            result = sandbox.run(call.function.name, json.loads(call.function.arguments or "{}"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return messages[-1].get("content") or ""


async def arun(task: str, sandbox: Sandbox, client: Any = None, model: str | None = None, max_steps: int = 6) -> str:
    """The same loop with the async client (openai.AsyncOpenAI)."""
    from openai import AsyncOpenAI

    client = client or AsyncOpenAI()
    model = model or os.environ.get("AGENT_MODEL", "openai/gpt-oss-120b")
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": task}]
    for _ in range(max_steps):
        reply = await client.chat.completions.create(model=model, messages=messages, tools=TOOLS, temperature=0)
        msg = reply.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))
        if not msg.tool_calls:
            return msg.content or ""
        for call in msg.tool_calls:
            result = sandbox.run(call.function.name, json.loads(call.function.arguments or "{}"))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    return messages[-1].get("content") or ""


if __name__ == "__main__":
    box = Sandbox(pages={"https://fixtures.test/solar.html": "Rooftop solar costs fell 12% this year."})
    print(run(" ".join(sys.argv[1:]) or "Summarise https://fixtures.test/solar.html", box))
    print("outbox:", box.outbox)
