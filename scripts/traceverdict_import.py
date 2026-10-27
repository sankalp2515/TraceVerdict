"""Import an original incident through the API. Keep TRACEVERDICT_ADMIN_KEY private."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/core"))
from intentseal_core.config import load_env  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--gateway", default="http://localhost:8000")
    parser.add_argument("--register-policy", type=Path, help="Current policy JSON for a new agent; preserves existing policies")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--investigate", action="store_true")
    args = parser.parse_args()
    load_env()
    token = os.environ.get("TRACEVERDICT_ADMIN_KEY")
    if not token:
        parser.error("Set TRACEVERDICT_ADMIN_KEY privately")
    original = args.capture.read_bytes()
    capture = json.loads(original)
    agent = capture["agent_id"]
    with httpx.Client(base_url=args.gateway.rstrip("/"), headers={"Authorization": "Bearer " + token}, timeout=40) as client:
        def request(path, body):
            response = client.post(path, json=body)
            if response.status_code >= 400:
                raise RuntimeError(f"API {path} returned HTTP {response.status_code}; inspect safe diagnostics")
            return response.json()
        if args.register_policy:
            request("/v1/agents", {"agent_id": agent, "policy": json.loads(args.register_policy.read_text(encoding="utf-8"))})
        snapshot = request("/v1/replay-snapshots", capture)
        case = request("/v1/cases", {"agent_id": agent, "snapshot_id": snapshot["snapshot_id"], "execution_mode": "live",
                       "idempotency_key": "capture-" + hashlib.sha256(original).hexdigest()})
        cid = case["case_id"]
        print(json.dumps({"case_id": cid, "snapshot_id": snapshot["snapshot_id"], "status": case["status"]}))
        if args.publish and case["status"] == "COLLECTING":
            result = request(f"/v1/cases/{cid}/publish-source-records", {})
            print(json.dumps({"published": result["published"], "sources": result["sources"]}))
        if args.investigate:
            job = request(f"/v1/cases/{cid}/investigate", {"idempotency_key": "capture-investigate-" + snapshot["manifest_sha256"]})
            print(json.dumps({"job_id": job["job_id"], "status": job["status"], "next": "Open this case in the workspace."}))


if __name__ == "__main__":
    main()
