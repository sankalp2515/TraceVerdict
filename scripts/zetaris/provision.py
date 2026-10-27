"""Provision owned synthetic sources and a real governed Zetaris semantic view.

Owner credentials stay in .env. Zetaris gets separate SELECT-only reader credentials.
DDL receipts store operation labels and result hashes, never connection SQL/passwords.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

import httpx
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "packages/core"))
from intentseal_core.config import load_env  # noqa: E402

GROUPS = {"events": (54331, "tv-events"), "configuration": (54332, "tv-configuration"), "reference": (54333, "tv-reference")}
SCOPE = "tenant_id, agent_id, case_id"
PROJECTION = "u.tenant_id,u.agent_id,u.case_id,u.evidence_kind,u.evidence_json"
VIEW_SQL = f"""SELECT {PROJECTION} FROM (
 SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_events.evidence
 UNION ALL SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_configuration.evidence
 UNION ALL SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM tv_reference.evidence
) u
JOIN tv_events.case_membership e ON u.tenant_id=e.tenant_id AND u.agent_id=e.agent_id AND u.case_id=e.case_id
JOIN tv_configuration.case_membership c ON u.tenant_id=c.tenant_id AND u.agent_id=c.agent_id AND u.case_id=c.case_id
JOIN tv_reference.case_membership r ON u.tenant_id=r.tenant_id AND u.agent_id=r.agent_id AND u.case_id=r.case_id"""
QUALITY_SQL = """SELECT tenant_id,agent_id,case_id,COUNT(*) AS row_count,
COUNT(DISTINCT evidence_kind) AS distinct_kinds
FROM traceverdict.case_evidence GROUP BY tenant_id,agent_id,case_id
HAVING COUNT(*) <> 7 OR COUNT(DISTINCT evidence_kind) <> 7"""


def connection(group):
    return psycopg.connect(host="127.0.0.1", port=GROUPS[group][0], dbname=group,
                          user="tv_owner", password=os.environ[f"TV_{group.upper()}_PASSWORD"], connect_timeout=10)


def initialize():
    for group in GROUPS:
        with connection(group) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS case_membership (tenant_id TEXT NOT NULL,agent_id TEXT NOT NULL,"
                         "case_id TEXT NOT NULL,source_version TEXT NOT NULL,PRIMARY KEY(tenant_id,agent_id,case_id))")
            conn.execute("CREATE TABLE IF NOT EXISTS evidence (tenant_id TEXT NOT NULL,agent_id TEXT NOT NULL,"
                         "case_id TEXT NOT NULL,evidence_id TEXT NOT NULL,evidence_kind TEXT NOT NULL,evidence_json TEXT NOT NULL,"
                         "PRIMARY KEY(tenant_id,agent_id,case_id,evidence_id))")
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='tv_reader'").fetchone():
                conn.execute(sql.SQL("CREATE ROLE tv_reader LOGIN PASSWORD {}").format(
                    sql.Literal(os.environ[f"TV_{group.upper()}_READER_PASSWORD"])))
            conn.execute("GRANT USAGE ON SCHEMA public TO tv_reader")
            conn.execute("GRANT SELECT ON case_membership,evidence TO tv_reader")
        print(json.dumps({"initialized": group, "zetaris_access": "SELECT only"}), flush=True)


def load_records(case_id, gateway):
    with httpx.Client(timeout=30) as client:
        response = client.get(f"{gateway}/v1/cases/{case_id}/source-records", headers={
            "Authorization": "Bearer " + os.environ["TRACEVERDICT_ADMIN_KEY"]})
        response.raise_for_status()
        records = response.json()
    groups = {g: [] for g in GROUPS}
    for record in records:
        group = "configuration" if record["kind"] in ("policy", "tools") else "reference" if record["kind"] == "reference" else "events"
        groups[group].append(record)
    if not all(groups.values()):
        raise ValueError("all three independently governed source groups are required")
    for group, rows in groups.items():
        with connection(group) as conn:
            scope = (rows[0]["tenant_id"], rows[0]["agent_id"], case_id)
            version = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
            old = conn.execute("SELECT source_version FROM case_membership WHERE tenant_id=%s AND agent_id=%s AND case_id=%s", scope).fetchone()
            if old and old[0] != version:
                raise ValueError("immutable registered case source changed")
            conn.execute("INSERT INTO case_membership VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", (*scope, version))
            for r in rows:
                conn.execute("INSERT INTO evidence VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                             (*scope, r["evidence_id"], r["kind"], json.dumps(r, separators=(",", ":"))))
        print(json.dumps({"loaded": group, "case_id": case_id, "records": len(rows), "source_version": version}), flush=True)


def query(statement):
    rid = str(uuid.uuid4())
    with httpx.Client(timeout=90) as client:
        response = client.post(os.environ["ZETARIS_REST_URL"].rstrip("/") + "/sql-editor/sqls/run", headers={
            "Authorization": "Bearer " + os.environ["ZETARIS_API_KEY"], "X-Org-ID": os.environ["ZETARIS_ORG_ID"],
            "X-Request-ID": rid}, json={"queryId": rid, "sql": statement, "source": "SqlEditor", "limit": 100})
        if response.status_code != 200:
            # Error bodies may contain the submitted connection SQL; never log them.
            raise RuntimeError(f"Zetaris query returned HTTP {response.status_code}")
        return response.json(), rid


def register():
    result, _ = query("SHOW DATASOURCES")
    existing = json.dumps(result)
    for group, (_, host) in GROUPS.items():
        name = "tv_" + group
        if name not in existing:
            password = os.environ[f"TV_{group.upper()}_READER_PASSWORD"].replace("'", "''")
            query(f"CREATE DATASOURCE {name} DESCRIBE BY 'TraceVerdict independent {group} database' OPTIONS ("
                  f"jdbcdriver 'org.postgresql.Driver',jdbcurl 'jdbc:postgresql://{host}:5432/{group}',"
                  f"username 'tv_reader',password '{password}')")
        tables, _ = query(f"SHOW DATASOURCE TABLES {name}")
        registered = json.dumps(tables)
        for table in ("evidence", "case_membership"):
            if '"' + table + '"' not in registered:
                query(f"REGISTER DATASOURCE TABLE '{table}' FROM {name}")
        print(json.dumps({"registered": name}), flush=True)
    containers, _ = query("SHOW DATASOURCE VIEWS")
    if "traceverdict" not in json.dumps(containers):
        # A repeat registration can find an existing empty container.
        try:
            query("CREATE SCHEMASTORE CONTAINER traceverdict")
        except RuntimeError:
            # Replacement below must still succeed; no false success is reported.
            pass
    # Repeated provisioning preserves the native USL application path if activated.
    try:
        query("LOAD USL cases NAMESPACE lightning.metastore.traceverdict")
        application_sql = "SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM lightning.metastore.traceverdict.cases.case_evidence"
    except RuntimeError:
        application_sql = VIEW_SQL
    query("CREATE OR REPLACE SCHEMASTORE VIEW case_evidence WITH CONTAINER traceverdict AS " + application_sql)
    output = ROOT / "artifacts/traceverdict/zetaris"
    output.mkdir(parents=True, exist_ok=True)
    (output / "semantic-view.sql").write_text("CREATE OR REPLACE SCHEMASTORE VIEW case_evidence WITH CONTAINER traceverdict AS\n" + VIEW_SQL, encoding="utf-8")
    print(json.dumps({"governed_view": "traceverdict.case_evidence", "three_source_join": True}), flush=True)


def verify():
    receipts = []
    checks = [(f"{group}-{label}", statement) for group in GROUPS for label, statement in [
        ("count", f"SELECT COUNT(*) AS records FROM tv_{group}.evidence"),
        ("kinds", f"SELECT evidence_kind,COUNT(*) AS records FROM tv_{group}.evidence GROUP BY evidence_kind"),
        ("membership", f"SELECT tenant_id,agent_id,COUNT(*) AS cases FROM tv_{group}.case_membership GROUP BY tenant_id,agent_id")]]
    checks += [("semantic-summary", "SELECT tenant_id,agent_id,case_id,evidence_kind FROM traceverdict.case_evidence"),
               ("semantic-kind-counts", "SELECT evidence_kind,COUNT(*) AS records FROM traceverdict.case_evidence GROUP BY evidence_kind"),
               ("case-completeness-quality-rule", QUALITY_SQL)]
    for label, statement in checks:
        started = time.monotonic()
        result, rid = query(statement)
        receipts.append({"check": label, "sql": statement, "request_id": rid, "result": result,
                         "duration_ms": round((time.monotonic() - started) * 1000)})
        print(json.dumps({"check": label, "rows": len(result.get("data", []))}), flush=True)
    quality = receipts[-1]["result"].get("data")
    if quality != []:
        raise ValueError("case-completeness quality rule returned violations")
    output = ROOT / "artifacts/traceverdict/zetaris"
    output.mkdir(parents=True, exist_ok=True)
    (output / "verification.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["init", "load", "register", "verify"])
    parser.add_argument("--case-id")
    parser.add_argument("--gateway", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    load_env()
    if args.operation == "load":
        if not args.case_id:
            parser.error("--case-id required")
        load_records(args.case_id, args.gateway.rstrip("/"))
    else:
        {"init": initialize, "register": register, "verify": verify}[args.operation]()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"operation_failed": type(exc).__name__}), flush=True)
        raise SystemExit(1) from None
