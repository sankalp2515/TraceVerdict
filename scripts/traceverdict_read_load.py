"""Bounded authenticated read-load smoke check; no model calls or customer writes."""
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/core"))
from intentseal_core.config import load_env  # noqa: E402


async def run(gateway: str, count: int, concurrency: int) -> dict:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(base_url=gateway, timeout=30,
                                 headers={"Authorization": "Bearer " + os.environ["TRACEVERDICT_PROJECT_KEY"]}) as client:
        async def probe():
            async with sem:
                start = time.monotonic()
                try:
                    response = await client.get("/v1/cases?limit=20")
                    return response.status_code, (time.monotonic() - start) * 1000
                except httpx.HTTPError:
                    return 0, (time.monotonic() - start) * 1000
        started = time.monotonic()
        results = await asyncio.gather(*(probe() for _ in range(count)))
    times = sorted(ms for _, ms in results)
    return {"check": "local-authenticated-case-list-read-smoke", "requests": count, "concurrency": concurrency,
            "statuses": dict(Counter(str(code) for code, _ in results)), "p50_ms": round(statistics.median(times), 2),
            "p95_ms": round(times[max(0, math.ceil(.95 * count) - 1)], 2),
            "elapsed_s": round(time.monotonic() - started, 2),
            "all_passed": all(code == 200 for code, _ in results),
            "scope": "Local operator deployment only; excludes inference, source ingestion, writes and browser rendering. Not a production capacity SLO."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway", default="http://localhost:5173/api")
    args = parser.parse_args()
    load_env()
    result = asyncio.run(run(args.gateway, 32, 4))
    out = ROOT / "examples/traceverdict/operations"
    out.mkdir(parents=True, exist_ok=True)
    (out / "read-load.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    if not result["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
