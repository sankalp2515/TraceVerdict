"""Activate a native Zetaris USL and run its native data-quality rule.

Only this project's namespace/model/view are changed. No source records are altered.
"""
import json

from provision import ROOT, VIEW_SQL, load_env, query

NAMESPACE = "lightning.metastore.traceverdict"
TABLE = NAMESPACE + ".cases.case_evidence"


def main():
    load_env()
    receipts = []

    def run(label, statement):
        result, rid = query(statement)
        receipts.append({"operation": label, "sql": statement, "request_id": rid, "result": result})
        print(json.dumps({"operation": label, "result": result}), flush=True)
        return result

    run("parent-namespace", "CREATE NAMESPACE IF NOT EXISTS lightning.metastore")
    run("namespace", f"CREATE NAMESPACE IF NOT EXISTS {NAMESPACE}")
    try:
        query(f"LOAD USL cases NAMESPACE {NAMESPACE}")
    except RuntimeError:
        run("compile-model", f"COMPILE USL cases DEPLOY NAMESPACE {NAMESPACE} DDL CREATE TABLE case_evidence ("
            "tenant_id varchar(64),agent_id varchar(64),case_id varchar(64),evidence_kind varchar(32),evidence_json varchar(65535))")
    run("activate-three-source-usl", f"ACTIVATE USL TABLE {TABLE} AS {VIEW_SQL}")
    rules = run("list-rules", f"LIST DQ USL {NAMESPACE}.cases")
    if "valid_evidence_payload" not in json.dumps(rules):
        run("register-quality-rule", f"REGISTER DQ valid_evidence_payload TABLE {TABLE} AS evidence_json IS NOT NULL "
            "AND LENGTH(evidence_json)>2 AND evidence_kind IN ('task','document','action','receipt','policy','tools','reference','event')")
    quality = run("execute-native-quality-rule", f"RUN DQ valid_evidence_payload TABLE {TABLE}")
    rows = quality.get("data", [])
    if not rows or any(int(row[-1]) != 0 or int(row[-3]) < 1 for row in rows):
        raise ValueError("Native data-quality rule failed or had no evidence records")
    run("query-native-usl", f"SELECT evidence_kind,COUNT(*) AS records FROM {TABLE} GROUP BY evidence_kind")
    # Keep the application contract stable while actually querying the activated USL.
    run("application-usl-view", "CREATE OR REPLACE SCHEMASTORE VIEW case_evidence WITH CONTAINER traceverdict AS "
        f"SELECT tenant_id,agent_id,case_id,evidence_kind,evidence_json FROM {TABLE}")
    output = ROOT / "artifacts/traceverdict/zetaris"
    output.mkdir(parents=True, exist_ok=True)
    (output / "native-usl.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    (output / "native-usl.sql").write_text(";\n\n".join(r["sql"] for r in receipts), encoding="utf-8")


if __name__ == "__main__":
    main()
