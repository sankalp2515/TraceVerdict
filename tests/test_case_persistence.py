"""Real connection contention and abrupt process loss, on SQLite and PostgreSQL."""
import asyncio
import json
import os
import subprocess
import sys
import time
from types import SimpleNamespace
import uuid

import pytest

from intentseal_core.policy import AgentPolicy
from intentseal_core.store import Store
from intentseal_gateway.cases.models import CreateCase
from intentseal_gateway.cases.service import CaseService
from intentseal_gateway.cases.world_state import Conflict, WorldState


@pytest.fixture(params=["sqlite", "postgres"])
def persistent_store(request, tmp_path):
    if request.param == "sqlite":
        target = str(tmp_path / "durable.db")
        store = Store(target)
        yield store, target
        store._conn.close()
        return
    url = os.environ.get("INTENTSEAL_TEST_DATABASE_URL")
    if not url:
        pytest.skip("PostgreSQL test connection not configured")
    import psycopg
    from psycopg import sql
    schema = "tv_test_" + uuid.uuid4().hex[:12]
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    target = url + ("&" if "?" in url else "?") + "options=-csearch_path%3D" + schema
    store = Store(target)
    try:
        yield store, target
    finally:
        store._conn.close()
        with psycopg.connect(url, autocommit=True) as admin:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def runtime(store):
    return SimpleNamespace(store=store, policy_loader=lambda agent: AgentPolicy(agent=agent))


def queue(world, case, jid):
    case["jobs"][jid] = {"job_id": jid, "kind": "investigate", "candidate_id": None,
                         "status": "queued", "lease_until": 0, "created_at": time.time(), "timeout_s": 180}
    return world.commit(case, case["state_version"], "controller", "job_queued")


async def test_global_claim_limit_and_atomic_history(persistent_store):
    store, target = persistent_store
    svc = CaseService(runtime(store))
    other_store = Store(target)
    other = WorldState(other_store)
    try:
        cases = [svc.create(CreateCase(agent_id="research-agent", fixture_id="supplier-contact",
                   execution_mode="sample", idempotency_key=f"global-limit-{i}"), "default") for i in range(3)]
        for i, case in enumerate(cases):
            current = queue(svc.world, case, f"job-{i}")
            current["jobs"][f"job-{i}"].update(status="running", lease_until=time.time() + 60)
            if i < 2:
                other.commit(current, current["state_version"], "worker", "job_claimed")
            else:
                with pytest.raises(Conflict, match="concurrency"):
                    other.commit(current, current["state_version"], "worker", "job_claimed")
        assert svc.world.active_count() == 3
        queued = svc.world.load(cases[2]["case_id"], "default")
        assert queued["jobs"]["job-2"]["status"] == "queued"
        # The rejected transaction did not add history or partially update an index.
        assert queued["state_version"] == 1
        assert svc.world.at_version(queued["case_id"], "default", 1)["jobs"]["job-2"]["status"] == "queued"
        assert "projection" not in queued["observations"][0]
    finally:
        await svc.close()
        other_store._conn.close()


async def test_recovery_after_actual_worker_process_termination(persistent_store, tmp_path):
    store, target = persistent_store
    svc = CaseService(runtime(store))
    case = svc.create(CreateCase(agent_id="research-agent", fixture_id="supplier-contact",
                     execution_mode="sample", idempotency_key="crash-recovery-001"), "default")
    case = queue(svc.world, case, "crash-job")
    marker = tmp_path / "worker-ready.json"
    code = """
import json,os,sys,time
from pathlib import Path
from intentseal_core.store import Store
from intentseal_gateway.cases.world_state import WorldState
w=WorldState(Store(os.environ['TV_CRASH_STORE']))
c=w.load(sys.argv[1],'default')
lease=time.time()+3
c['jobs']['crash-job'].update(status='running',lease_until=lease)
w.commit(c,c['state_version'],'worker','job_claimed')
Path(sys.argv[2]).write_text(json.dumps({'lease_until':lease}))
while True:time.sleep(1)
"""
    child = subprocess.Popen([sys.executable, "-c", code, case["case_id"], str(marker)],
                             env={**os.environ, "TV_CRASH_STORE": target}, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    recovery = None
    try:
        until = time.monotonic() + 15
        while not marker.exists() and child.poll() is None and time.monotonic() < until:
            await asyncio.sleep(.05)
        assert marker.exists(), "worker did not claim the durable job"
        child.terminate()
        child.wait(timeout=10)
        assert svc.world.load(case["case_id"], "default")["jobs"]["crash-job"]["status"] == "running"
        lease = json.loads(marker.read_text())["lease_until"]
        await asyncio.sleep(max(0, lease - time.time()) + .1)
        recovery = asyncio.create_task(svc.recover())
        until = time.monotonic() + 15
        while time.monotonic() < until:
            current = svc.world.load(case["case_id"], "default")
            if current["jobs"]["crash-job"]["status"] == "complete":
                break
            await asyncio.sleep(.05)
        assert current["status"] == "PROPOSING"
        assert current["jobs"]["crash-job"]["status"] == "complete"
        assert len({c["candidate_id"] for c in current["candidates"]}) == 2
        assert svc.world.active_count() == 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=10)
        if recovery:
            recovery.cancel()
            await asyncio.gather(recovery, return_exceptions=True)
        await svc.close()


def test_connection_loss_never_replays_half_a_transaction(persistent_store):
    store, target = persistent_store
    if store.backend != "postgres":
        pytest.skip("connection termination is a PostgreSQL fault-injection check")
    import psycopg
    store.ensure_schema(["CREATE TABLE transaction_probe(id INTEGER PRIMARY KEY)"])
    other = Store(target)
    try:
        pid = store.query("SELECT pg_backend_pid() AS pid")[0]["pid"]
        with pytest.raises(psycopg.OperationalError):
            with store.transaction():
                store.execute("INSERT INTO transaction_probe VALUES(?)", (1,))
                # Terminate only the dedicated test connection, not an app/vendor process.
                other.query("SELECT pg_terminate_backend(?) AS terminated", (pid,))
                store.execute("INSERT INTO transaction_probe VALUES(?)", (2,))
        assert other.query("SELECT * FROM transaction_probe") == []
    finally:
        other._conn.close()
