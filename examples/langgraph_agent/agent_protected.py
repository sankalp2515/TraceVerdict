"""The agent.py LangGraph agent behind the IntentSeal SDK; the diff between the two files is the adoption cost.

    OPENAI_API_KEY=<groq key> python agent_protected.py "Summarise https://fixtures.test/solar.html"

Tools are sandboxed: pages come from a dict, email goes to an in-memory outbox.
"""

from __future__ import annotations

import os
import sys

from asg_sdk import Guard
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

PAGES = {"https://fixtures.test/solar.html": "Rooftop solar costs fell 12% this year."}
OUTBOX: list[dict[str, str]] = []


@tool
def web_fetch(url: str) -> str:
    """Fetch a web page and return its text."""
    return PAGES.get(url, "404 not found")


@tool
def send_message(to: str, subject: str, body: str) -> str:
    """Send an email message."""
    OUTBOX.append({"to": to, "subject": subject, "body": body})
    return "sent"


TOOLS = [web_fetch, send_message]


def make_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=os.environ.get("AGENT_MODEL", "openai/gpt-oss-120b"), temperature=0,
                      base_url=os.environ.get("OPENAI_BASE_URL", "https://api.groq.com/openai/v1"))


def run(task: str, model=None, guard: Guard | None = None) -> str:
    guard = guard or Guard("research-agent")
    with guard.session(task=task):
        agent = create_react_agent(model or make_model(), guard.protect_tools(TOOLS))
        out = agent.invoke({"messages": [("user", task)]})
    return out["messages"][-1].content


if __name__ == "__main__":
    print(run(" ".join(sys.argv[1:]) or "Summarise https://fixtures.test/solar.html"))
    print("outbox:", OUTBOX)
