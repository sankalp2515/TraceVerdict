"""Command line: `intentseal providers check [--no-call] [--models]`.

Prints providers, key *aliases* and health, and makes one minimal test call per key.
Key values are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import load_settings
from .llm.adapters import ChatRequest, ProviderError
from .llm.router import Router


def _check_model(settings, provider: str) -> str | None:
    p = settings.providers[provider]
    if p.options.get("check_model"):
        return str(p.options["check_model"])
    for role in settings.roles.values():
        for m in role.models:
            if m.provider == provider:
                return m.model
    return None


async def providers_check(call: bool, show_models: bool) -> int:
    settings = load_settings()
    router = Router(settings)
    bad = 0
    try:
        configured = {(m.provider, m.model) for r in settings.roles.values() for m in r.models}
        for name, p in sorted(settings.providers.items(), key=lambda kv: kv[1].priority):
            aliases = ", ".join(k.alias for k in p.keys) or "-"
            print(f"\n[{name}] type={p.type} priority={p.priority} keys={len(p.keys)} ({aliases})")
            print(f"  status: {router.provider_status(name)}")
            if not p.active:
                continue
            if show_models:
                try:
                    ids = await router.list_models(name)
                    print(f"  models available: {len(ids)}")
                    for prov, model in sorted(configured):
                        if prov == name:
                            found = model in ids or f"models/{model}" in ids
                            print(f"    configured {model}: {'FOUND' if found else 'NOT LISTED'}")
                except ProviderError as e:
                    print(f"  models: error {e.kind}")
            if not call:
                continue
            model = _check_model(settings, name)
            if not model:
                print("  test call: skipped (no model configured for this provider)")
                continue
            for key in p.keys:
                req = ChatRequest(messages=[{"role": "user", "content": "Reply with the single word: ok"}],
                                  max_tokens=64, temperature=0)
                try:
                    r = await router.call_direct(name, model, req, key=key)
                    text = (r.content or "").strip().replace("\n", " ")[:20]
                    print(f"  {key.alias}: OK  {r.latency_ms:.0f} ms  model={model}  reply='{text}'")
                except ProviderError as e:
                    bad += 1
                    print(f"  {key.alias}: FAIL {e.kind} (HTTP {e.http_status})  model={model}")
    finally:
        await router.aclose()
    return 1 if bad else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="intentseal")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("providers", help="provider operations")
    prs = pr.add_subparsers(dest="sub", required=True)
    chk = prs.add_parser("check", help="list providers, key aliases, health; test each key")
    chk.add_argument("--no-call", action="store_true", help="do not make test calls")
    chk.add_argument("--models", action="store_true", help="verify configured model IDs against /models")
    args = ap.parse_args(argv)
    if args.cmd == "providers" and args.sub == "check":
        return asyncio.run(providers_check(call=not args.no_call, show_models=args.models))
    return 2


if __name__ == "__main__":
    sys.exit(main())
