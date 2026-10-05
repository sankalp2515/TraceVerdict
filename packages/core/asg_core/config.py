"""Configuration loading. Providers and models come from YAML; keys and paths from the environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .secrets import ApiKey, load_keys


def repo_root() -> Path:
    env = os.environ.get("ASG_HOME")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "config" / "providers.yaml").exists():
            return parent
    return Path.cwd()


def load_env() -> None:
    load_dotenv(repo_root() / ".env", override=False)


@dataclass
class ProviderConfig:
    name: str
    type: str
    enabled: bool
    base_url: str
    keys: list[ApiKey]
    priority: int = 50
    timeout_s: float = 30
    connect_timeout_s: float = 5
    retries: int = 1
    backoff_base_s: float = 1.0
    backoff_max_s: float = 60
    circuit_failures: int = 3
    circuit_open_s: float = 60
    key_rotation: str = "on_auth_failure"
    rpm: float | None = None
    daily_token_budget: int | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)

    @property
    def active(self) -> bool:
        return self.enabled and bool(self.keys)

    @property
    def disabled_reason(self) -> str | None:
        if not self.enabled:
            return "disabled in config"
        if not self.keys:
            return "no keys in environment"
        return None


@dataclass
class ModelRef:
    provider: str
    model: str
    price_in: float = 0.0   # USD per million input tokens (list price, for reporting)
    price_out: float = 0.0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleConfig:
    name: str
    models: list[ModelRef]
    cache: bool = True
    cache_ttl_s: int = 86400
    defaults: dict[str, Any] = field(default_factory=dict)


@dataclass
class Settings:
    providers: dict[str, ProviderConfig]
    roles: dict[str, RoleConfig]
    db_path: Path


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_providers(path: Path | None = None) -> dict[str, ProviderConfig]:
    path = path or repo_root() / "config" / "providers.yaml"
    raw = _read_yaml(path)
    defaults = raw.get("defaults", {}) or {}
    out: dict[str, ProviderConfig] = {}
    for name, p in (raw.get("providers") or {}).items():
        merged = {**defaults, **p}
        keys_cfg = merged.get("keys") or {}
        limits = merged.get("limits") or {}
        budget = merged.get("budget") or {}
        known = {
            "type", "enabled", "base_url", "keys", "priority", "timeout_s", "connect_timeout_s",
            "retries", "backoff_base_s", "backoff_max_s", "circuit_failures", "circuit_open_s",
            "key_rotation", "limits", "budget", "extra_headers",
        }
        out[name] = ProviderConfig(
            name=name,
            type=merged.get("type", "openai_compatible"),
            enabled=bool(merged.get("enabled", True)),
            base_url=str(merged.get("base_url", "")).rstrip("/"),
            keys=load_keys(name, keys_cfg.get("env_prefix"), keys_cfg.get("env_list")),
            priority=int(merged.get("priority", 50)),
            timeout_s=float(merged.get("timeout_s", 30)),
            connect_timeout_s=float(merged.get("connect_timeout_s", 5)),
            retries=int(merged.get("retries", 1)),
            backoff_base_s=float(merged.get("backoff_base_s", 1.0)),
            backoff_max_s=float(merged.get("backoff_max_s", 60)),
            circuit_failures=int(merged.get("circuit_failures", 3)),
            circuit_open_s=float(merged.get("circuit_open_s", 60)),
            key_rotation=str(merged.get("key_rotation", "on_auth_failure")),
            rpm=limits.get("rpm"),
            daily_token_budget=budget.get("daily_tokens"),
            extra_headers=dict(merged.get("extra_headers") or {}),
            options={k: v for k, v in merged.items() if k not in known},
        )
    return out


def load_roles(path: Path | None = None) -> dict[str, RoleConfig]:
    path = path or repo_root() / "config" / "models.yaml"
    raw = _read_yaml(path)
    out: dict[str, RoleConfig] = {}
    for name, r in (raw.get("roles") or {}).items():
        models = [
            ModelRef(
                provider=m["provider"],
                model=m["model"],
                price_in=float((m.get("price_per_mtok") or {}).get("input", 0.0)),
                price_out=float((m.get("price_per_mtok") or {}).get("output", 0.0)),
                params=dict(m.get("params") or {}),
            )
            for m in r.get("models", [])
        ]
        out[name] = RoleConfig(
            name=name,
            models=models,
            cache=bool(r.get("cache", True)),
            cache_ttl_s=int(r.get("cache_ttl_s", 86400)),
            defaults=dict(r.get("defaults") or {}),
        )
    return out


def load_settings() -> Settings:
    load_env()
    db = Path(os.environ.get("ASG_DB_PATH") or repo_root() / "data" / "asg.db")
    return Settings(providers=load_providers(), roles=load_roles(), db_path=db)
