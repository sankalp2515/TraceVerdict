"""Load test of one gateway process: fast-path inspections (user messages, local classifier, no AI call) and action
checks (rules only), at a fixed concurrency, with unique content so no cache answers. Prints throughput and latency.

    python -m intentseal_eval.load --url http://127.0.0.1:8030 --key <project key> --agent my-assistant
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import statistics
import string
import time
from pathlib import Path

import httpx

WORDS = ("report revenue meeting customer invoice schedule review policy travel refund summary quarter team project "
         "budget forecast product release update notes agenda client contract renewal support ticket").split()


def message(rng: random.Random) -> str:
    tag = "".join(rng.choices(string.ascii_lowercase, k=6))
    return f"Please {rng.choice(['summarise', 'check', 'list', 'draft'])} the " + " ".join(rng.choices(WORDS, k=12)) + f" ({tag})."


async def run(url: str, key: str, agents: list[str], kind: str, n: int, concurrency: int) -> dict:
    rng = random.Random(time.time_ns())   # fresh content every run: no cache answers
    lat: list[float] = []
    errors = 0
    sem = asyncio.Semaphore(concurrency)
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(base_url=url, headers=headers, timeout=60) as c:
        sids = {a: (await c.post("/v1/sessions", json={"agent_id": a, "task": "Summarise the quarterly report"})).json()["session_id"]
                for a in agents}

        async def one(i: int) -> None:
            nonlocal errors
            async with sem:
                agent = agents[i % len(agents)]
                sid = sids[agent]
                t0 = time.perf_counter()
                if kind == "inspect":
                    r = await c.post("/v1/inspect", json={"content": message(rng), "source": "user", "agent_id": agent,
                                                         "session_id": f"{sid}-{i % 50}"})
                else:
                    r = await c.post("/v1/actions/check", json={"tool": "read_file", "args": {"path": f"notes/{i}.md"},
                                                               "agent_id": agent, "session_id": sid})
                lat.append((time.perf_counter() - t0) * 1000)
                errors += r.status_code != 200
        t0 = time.perf_counter()
        await asyncio.gather(*(one(i) for i in range(n)))
        wall = time.perf_counter() - t0
    lat.sort()
    return {"kind": kind, "agents": len(agents), "requests": n, "concurrency": concurrency, "errors": errors, "seconds": round(wall, 1),
            "throughput_rps": round(n / wall, 1), "p50_ms": round(statistics.median(lat), 1),
            "p95_ms": round(lat[int(len(lat) * 0.95) - 1], 1), "max_ms": round(lat[-1], 1)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8030")
    ap.add_argument("--key", required=True)
    ap.add_argument("--agent", default="my-assistant", help="comma list: decisions for one agent are serialised")
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    agents = [x for x in a.agent.split(",") if x]
    results = [asyncio.run(run(a.url, a.key, agents, kind, a.n, a.concurrency)) for kind in ("actions", "inspect")]
    for r in results:
        print(json.dumps(r))
    if a.out:
        Path(a.out).write_text(json.dumps({"date": time.strftime("%Y-%m-%d"), "url": a.url, "note":
                                           "one gateway process on the evaluation machine (CPU only), per-key rate limit lifted; user-message "
                                           "inspections use the local classifier (no AI call); action checks are rules",
                                           "results": results}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
