"""Per-agent policy (PRD §9), loaded from policies/<agent>.yaml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .config import repo_root


class ToolPolicy(BaseModel):
    risk: str = "low"                                   # low | medium | high
    failure: str = "open"                               # open | closed (SDK-5)
    pinned: list[str] = Field(default_factory=list)     # args always taken from trusted context
    escalate_if_uncertain: bool = False
    allowed_recipients: list[str] = Field(default_factory=list)   # "@domain" suffixes or exact addresses
    recipient_arg: str = "to"
    allowed_domains: list[str] = Field(default_factory=list)      # for URL-taking tools
    url_arg: str = "url"
    path_arg: str | None = None                         # argument holding a file path (sandbox check)


class Thresholds(BaseModel):
    neutralise: float = 0.6
    block: float = 0.85
    escalate_band: tuple[float, float] = (0.5, 0.85)


class SessionPolicy(BaseModel):
    risk_decay_per_turn: float = 0.2
    block_at: float = 1.5
    escalate_at: float = 0.8


class Budgets(BaseModel):
    daily_tokens_tier2: int | None = None
    on_exceeded: str = "rules_only_hold_high_risk"


class SensitiveData(BaseModel):
    patterns: list[str] = Field(default_factory=lambda: ["api_key", "credential"])
    canaries: list[str] = Field(default_factory=list)   # literal values; "from_env" reads ASG_CANARIES
    drop_non_visible: bool = True                       # untrusted docs: the model sees what a human sees


class AgentPolicy(BaseModel):
    agent: str
    mode: str = "monitor"                               # monitor | enforce
    task_scope: str = ""
    tools: dict[str, ToolPolicy] = Field(default_factory=dict)
    unknown_tools: str = "block"                        # block | allow
    sensitive_data: SensitiveData = Field(default_factory=SensitiveData)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    session: SessionPolicy = Field(default_factory=SessionPolicy)
    budgets: Budgets = Field(default_factory=Budgets)
    decision_model: str = "generative_free"
    version: str = "1"

    def canary_values(self) -> list[str]:
        out: list[str] = []
        for c in self.sensitive_data.canaries:
            if c == "from_env":
                out += [v.strip() for v in os.environ.get("ASG_CANARIES", "").split(",") if v.strip()]
            else:
                out.append(c)
        return out


def load_policy(agent: str, directory: Path | None = None) -> AgentPolicy:
    d = directory or repo_root() / "policies"
    path = d / f"{agent}.yaml"
    raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {"agent": agent}
    raw.setdefault("agent", agent)
    return AgentPolicy.model_validate(raw)
