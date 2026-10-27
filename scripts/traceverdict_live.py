"""Reproducible live acceptance through the authenticated public case API.

All incidents and executors are synthetic/local; Zetaris and Nightshift calls are real.
No approval is fabricated, and a failed stage is retained rather than bypassed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/core"))
from intentseal_core.config import load_env  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default="supplier-contact", choices=["supplier-contact", "invoice-forward", "report-notify"])
    parser.add_argument("--run-key", default="live-acceptance-v1")
    parser.add_argument("--gateway", default="http://127.0.0.1:8000")
    parser.add_argument("--comparison-control", action="store_true", help="Add an explicitly API-proposed disruptive negative control when one model candidate exists")
    args = parser.parse_args()
    load_env()
    headers = {"Authorization": "Bearer " + os.environ["TRACEVERDICT_ADMIN_KEY"]}
    with httpx.Client(base_url=args.gateway, headers=headers, timeout=30) as client:
        def request(method, path, body=None):
            response = client.request(method, path, json=body)
            if response.status_code >= 400:
                raise RuntimeError(f"API {method} {path} returned {response.status_code}")
            return response.json()
        case = request("POST", "/v1/cases", {"agent_id": "research-agent", "fixture_id": args.fixture,
                       "execution_mode": "live", "idempotency_key": args.run_key + "-" + args.fixture})
        cid = case["case_id"]
        print(json.dumps({"case_id": cid, "fixture": args.fixture, "mode": "live", "status": case["status"]}), flush=True)
        if not case["entities"]:
            subprocess.run([sys.executable, str(ROOT / "scripts/zetaris/provision.py"), "load", "--case-id", cid,
                            "--gateway", args.gateway], cwd=ROOT, check=True)
        def wait(job):
            until = time.monotonic() + job.get("timeout_s", 180) + 30
            while time.monotonic() < until:
                current = request("GET", f"/v1/cases/{cid}/jobs/{job['job_id']}")
                if current["status"] in ("complete", "incomplete"):
                    state = request("GET", f"/v1/cases/{cid}")
                    print(json.dumps({"job": current["kind"], "job_status": current["status"], "case_status": state["status"]}), flush=True)
                    return state
                time.sleep(2)
            raise TimeoutError("acceptance polling deadline")
        if case["status"] == "COLLECTING":
            job = request("POST", f"/v1/cases/{cid}/investigate", {"idempotency_key": args.run_key + "-investigate"})
            case = wait(job)
        if args.comparison_control and case["status"] == "PROPOSING" and len(case["candidates"]) == 1:
            accepted = [c["claim_id"] for c in case["claims"] if c["review_status"] == "accepted"]
            references = [e["payload"] for e in case["entities"].values() if e["kind"] == "reference"]
            if accepted and references and references[0].get("inactive_recipient"):
                request("POST", f"/v1/cases/{cid}/repairs", {"operations": [{"path": "tools.send_message.allowed_recipients", "value": [references[0]["inactive_recipient"]]}],
                    "rationale_claim_ids": accepted[:1], "expected_control_effect": "Explicit negative comparison control: restrict recipients and measure the expected loss of legitimate messaging utility."})
                case = request("GET", f"/v1/cases/{cid}")
        if case["status"] in ("PROPOSING", "VALIDATING"):
            for candidate in case["candidates"]:
                if candidate["candidate_id"] in case["validations"]:
                    continue
                job = request("POST", f"/v1/repairs/{candidate['candidate_id']}/validate",
                              {"idempotency_key": args.run_key + "-" + candidate["candidate_id"]})
                case = wait(job)
                if case["status"] == "INCOMPLETE":
                    break
        output = ROOT / "artifacts/traceverdict/live" / cid
        output.mkdir(parents=True, exist_ok=True)
        (output / "case.json").write_text(json.dumps(case, indent=2), encoding="utf-8")
        (output / "report.json").write_text(json.dumps(request("GET", f"/v1/cases/{cid}/export"), indent=2), encoding="utf-8")
        print(json.dumps({"case_id": cid, "status": case["status"], "errors": case["errors"],
                          "candidates": len(case["candidates"]), "models": sorted({r.get("actual_model_evidence") or "unattributed" for r in case["model_calls"]})}), flush=True)
        if case["status"] not in ("AWAITING_REVIEW", "APPROVED", "REJECTED"):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
