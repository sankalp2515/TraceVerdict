"""Outbound scan: stop secrets, credentials and canaries from leaving through a tool call.

Uses detect-secrets (Apache-2.0) specific detectors (entropy detectors excluded: too noisy on prose),
plus literal canaries and values registered at runtime. Hits are reported by type only, never by value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from detect_secrets.core.scan import scan_line
from detect_secrets.settings import default_settings

_NOISY = ("High Entropy",)


@dataclass(frozen=True)
class OutboundHit:
    kind: str          # "canary" | "secret:<detector>" | "registered"
    field: str         # argument name where it was found


def _strings(args: Any, prefix: str = "") -> Iterable[tuple[str, str]]:
    if isinstance(args, dict):
        for k, v in args.items():
            yield from _strings(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(args, (list, tuple)):
        for i, v in enumerate(args):
            yield from _strings(v, f"{prefix}[{i}]")
    elif args is not None:
        yield prefix or "value", str(args)


def scan_args(args: Any, canaries: Iterable[str] = (), registered: Iterable[str] = ()) -> list[OutboundHit]:
    canaries = [c for c in canaries if c and len(c) >= 6]
    registered = [r for r in registered if r and len(r) >= 6]
    hits: list[OutboundHit] = []
    with default_settings():
        for field_name, value in _strings(args):
            low = value.lower()
            if any(c.lower() in low for c in canaries):
                hits.append(OutboundHit("canary", field_name))
            if any(r.lower() in low for r in registered):
                hits.append(OutboundHit("registered", field_name))
            for line in value.splitlines() or [value]:
                for s in scan_line(line):
                    if not any(n in s.type for n in _NOISY):
                        hits.append(OutboundHit(f"secret:{s.type}", field_name))
    return sorted(set(hits), key=lambda h: (h.field, h.kind))
