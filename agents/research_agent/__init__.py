"""Reference Research Agent: the sandboxed agent the gateway protects in demos and evaluation."""

from .agent import ActionVerdict, AgentHooks, ResearchAgent, Transcript
from .world import ALLOWED_RECIPIENT_DOMAIN, World

__all__ = ["ResearchAgent", "AgentHooks", "ActionVerdict", "Transcript", "World", "ALLOWED_RECIPIENT_DOMAIN"]
