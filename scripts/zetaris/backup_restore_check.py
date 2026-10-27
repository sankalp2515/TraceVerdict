"""Back up all three local sources and restore each into a disposable check database.

Original databases and volumes are never deleted. Dumps contain private incident data
and stay in the ignored artifacts directory. Requires the running local Compose stack.
"""
import json
import subprocess
import uuid

from provision import GROUPS, ROOT, connection, load_env


def docker(group, command, data=None):
    base = ["docker", "compose", "-f", str(ROOT / "compose.data.yml"), "exec", "-T", "tv-" + group]
    result = subprocess.run(base + command, input=data, capture_output=True, cwd=ROOT)
    if result.returncode:
        raise RuntimeError("Backup/restore command failed; vendor output suppressed")
    return result.stdout


def main():
    load_env()
    output = ROOT / "artifacts/traceverdict/backups" / uuid.uuid4().hex[:12]
    output.mkdir(parents=True)
    receipts = []
    for group in GROUPS:
        scratch = "tv_restore_" + uuid.uuid4().hex[:16]
        dump = docker(group, ["pg_dump", "-U", "tv_owner", "-d", group, "-Fc"])
        (output / (group + ".dump")).write_bytes(dump)
        docker(group, ["createdb", "-U", "tv_owner", scratch])
        try:
            docker(group, ["pg_restore", "-U", "tv_owner", "--exit-on-error", "-d", scratch], dump)
            sql = "SELECT COUNT(*) FROM evidence"
            count = docker(group, ["psql", "-U", "tv_owner", "-d", scratch, "-Atc", sql]).decode().strip()
            with connection(group) as conn:
                original = conn.execute(sql).fetchone()[0]
            if int(count) != original:
                raise ValueError("Restored evidence count mismatch; retry with writers quiesced")
            receipts.append({"source": group, "restored_evidence_records": original, "restored": True})
            print(json.dumps(receipts[-1]), flush=True)
        finally:
            # Only this invocation's explicit disposable database is removed.
            docker(group, ["dropdb", "-U", "tv_owner", scratch])
    (output / "restore-check.json").write_text(json.dumps(receipts, indent=2), encoding="utf-8")
    print("Backup and isolated restore checks complete; private dumps remain under ignored artifacts.")


if __name__ == "__main__":
    main()
