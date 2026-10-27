"""Export three separately governed source groups from an authorized admin endpoint.

Use the project API key from TRACEVERDICT_ADMIN_KEY, never a command-line argument.
This prepares registration files; it does not claim to register sources in Zetaris.
"""
import argparse
import json
import os
from pathlib import Path

import httpx


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case_id")
    p.add_argument("--gateway", default="http://127.0.0.1:8000")
    p.add_argument("--output", type=Path, default=Path("artifacts/zetaris"))
    args = p.parse_args()
    if not args.case_id.startswith("case_") or not args.case_id[5:].isalnum():
        p.error("invalid case id")
    key = os.environ.get("TRACEVERDICT_ADMIN_KEY")
    if not key:
        p.error("TRACEVERDICT_ADMIN_KEY is required")
    response = httpx.get(f"{args.gateway.rstrip('/')}/v1/cases/{args.case_id}/source-records",
                         headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if response.status_code != 200:
        raise SystemExit(f"source export failed with HTTP {response.status_code}")
    groups = {"events": [], "configuration": [], "reference": []}
    for record in response.json():
        kind = record["kind"]
        group = "configuration" if kind in ("policy", "tools") else "reference" if kind == "reference" else "events"
        groups[group].append({"tenant_id": record["tenant_id"], "agent_id": record["agent_id"],
                              "case_id": record["case_id"], "evidence_kind": kind,
                              "evidence_json": json.dumps(record, separators=(",", ":"))})
    args.output.mkdir(parents=True, exist_ok=True)
    for group, rows in groups.items():
        (args.output / f"{group}.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(json.dumps({"case_id": args.case_id, "counts": {k: len(v) for k, v in groups.items()},
                      "registered_in_zetaris": False}))


if __name__ == "__main__":
    main()
