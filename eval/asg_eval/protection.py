"""Protection ON for the reference agent: the SDK Guard attached through the agent's hook points.

This is also the worked example of SDK adoption (G8): the agent's code is unchanged; a hooks object
routes user turns and tool results through `guard.ainspect` and every tool call through `guard.acheck`.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from asg_sdk import Decision, Guard
from research_agent import ActionVerdict, AgentHooks, World

AGENT_ID = "research-agent"
TRUSTED_CONTEXT = {"customer_id": "C-1042"}   # the signed-in user's own customer record (pinned field)
EXT_SOURCE = {".pdf": "pdf", ".docx": "docx", ".eml": "email", ".md": "markdown", ".html": "html", ".htm": "html",
              ".json": "api", ".png": "image", ".jpg": "image", ".jpeg": "image", ".py": "code", ".js": "code"}


@lru_cache(maxsize=1)
def shared_guard() -> Guard:
    return Guard(AGENT_ID)   # one engine per process: classifier loaded once, caches shared


class GuardHooks(AgentHooks):
    def __init__(self, guard: Guard, world: World, task: Any) -> None:
        self.guard = guard
        self.world = world
        first = task if isinstance(task, str) else (task[0] if task else "")
        self.session = guard.engine.start_session(AGENT_ID, user_ref="eval-user", task=first, trusted=dict(TRUSTED_CONTEXT))
        guard.register_secrets(world.canaries.values())

    async def on_content(self, source: str, content: str, meta: dict[str, Any]) -> str:
        sid = self.session.session_id
        if source == "user":
            # The signed-in user is trusted: a customer they name becomes the trusted (pinned) value.
            ids = re.findall(r"\bC-\d{4}\b", content)
            if ids:
                self.session.trusted["customer_id"] = ids[-1]
                self.session.note_trusted(content)
            return await self.guard.ainspect(content, "user", session_id=sid)
        tool = meta.get("tool")
        if tool == "read_file":
            path = str((meta.get("args") or {}).get("path", ""))
            p = (self.world.workspace / path.lstrip("/\\")).resolve()
            if p.is_file() and str(p).startswith(str(self.world.workspace.resolve())):
                return await self.guard.ainspect(p.read_bytes(), EXT_SOURCE.get(p.suffix.lower(), "text"),
                                                 filename=p.name, session_id=sid)
            return await self.guard.ainspect(content, "text", session_id=sid)
        if tool == "web_fetch":
            url = str((meta.get("args") or {}).get("url", ""))
            src = "api" if url.endswith(".json") else "web"
            return await self.guard.ainspect(content, src, filename=Path(url).name or None, session_id=sid)
        if tool == "read_email":
            return await self.guard.ainspect(content, "email", filename="inbox.json", session_id=sid)
        if tool == "query_db":
            return await self.guard.ainspect(content, "db", filename="record.json", session_id=sid)
        return await self.guard.ainspect(content, f"tool:{tool}", session_id=sid)

    async def on_action(self, tool: str, args: dict[str, Any], meta: dict[str, Any]) -> ActionVerdict:
        r = await self.guard.acheck(tool, args, session_id=self.session.session_id)
        if r.enforced == Decision.ALLOW:
            return ActionVerdict(True, r.final_args or args)
        return ActionVerdict(False, None, r.notice)


def guard_hooks(world: World, task: Any) -> GuardHooks:
    return GuardHooks(shared_guard(), world, task)
