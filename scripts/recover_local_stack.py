"""Warm the installed governed model after restart; never print credentials or raw errors.

Run inside case-api (environment already configured), or from a configured Python shell.
This loads an existing USL definition, not provisioning or replacing source data.
"""
from __future__ import annotations

import os
import time
import uuid

import httpx


def main() -> None:
    base = os.environ["ZETARIS_REST_URL"].rstrip("/")
    headers = {"Authorization": "Bearer " + os.environ["ZETARIS_API_KEY"],
               "X-Org-ID": os.environ["ZETARIS_ORG_ID"]}
    with httpx.Client(timeout=45) as client:
        for attempt in range(1, 6):
            try:
                for statement in (
                    "LOAD USL cases NAMESPACE lightning.metastore.traceverdict",
                    "SELECT evidence_kind FROM traceverdict.case_evidence LIMIT 1",
                ):
                    rid = str(uuid.uuid4())
                    response = client.post(base + "/sql-editor/sqls/run",
                                           headers={**headers, "X-Request-ID": rid},
                                           json={"queryId": rid, "sql": statement,
                                                 "source": "SqlEditor", "limit": 1})
                    response.raise_for_status()
                    if not isinstance(response.json().get("data"), list):
                        raise ValueError("Unsupported query response")
                print("Zetaris: existing USL loaded; real governed query passed.", flush=True)
                break
            except (httpx.HTTPError, ValueError):
                print(f"Zetaris warm-up attempt {attempt}/5 did not pass.", flush=True)
                if attempt == 5:
                    raise SystemExit("Governed evidence unavailable; inspect platform health privately.") from None
                time.sleep(2)
        for attempt in range(1, 4):
            response = client.get("http://127.0.0.1:8000/v1/connections",
                                  headers={"Authorization": "Bearer " + os.environ["TRACEVERDICT_ADMIN_KEY"]})
            response.raise_for_status()
            connections = response.json()
            if all(connections.get(name, {}).get("online") is True
                   for name in ("database", "zetaris", "nightshift")):
                break
            print(f"Authenticated dependency probe {attempt}/3 is not yet ready.", flush=True)
            if attempt < 3:
                time.sleep(2)
        for service in ("database", "zetaris", "nightshift"):
            online = connections.get(service, {}).get("online") is True
            print(f"{service}: {'online' if online else 'UNAVAILABLE'}", flush=True)
            if not online:
                raise SystemExit(f"{service} readiness has not passed.")


if __name__ == "__main__":
    main()
