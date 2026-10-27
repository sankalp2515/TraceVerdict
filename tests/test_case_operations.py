from fastapi.testclient import TestClient
import time

from intentseal_gateway.app import create_app
from intentseal_gateway.security import Principal


def test_operations_requires_reviewer_and_hides_other_tenants(tv_engine, tv_request, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "reviewer:ops-admin:admin:default,developer:ops-project:project:default")
    with TestClient(create_app(tv_engine)) as client:
        client.app.state.keys.add("other-admin", Principal("other", "admin", "foreign"))
        assert client.get("/v1/operations").status_code == 401
        assert client.get("/v1/operations", headers={"Authorization": "Bearer ops-project"}).status_code == 403
        store = tv_engine.store
        store.execute("INSERT INTO tv_worlds VALUES(?,?,?,?,?,?)", ("foreign-case", "foreign", "research-agent", 0, "h", "{}"))
        store.execute("INSERT INTO tv_job_index VALUES(?,?,?,?)", ("foreign-job", "foreign-case", "incomplete", 0))
        local = client.get("/v1/operations", headers={"Authorization": "Bearer ops-admin"}).json()
        assert local["jobs_by_status"] == {}
        assert local["database_online"] is True
        assert local["configured_global_running_limit"] == 2
        assert local["queue_attention"] is False
        assert "foreign-case" not in str(local)
        client.app.state.cases.stopping = True
        case = client.app.state.cases.create(tv_request, "default")
        case["jobs"]["queued-test"] = {"job_id": "queued-test", "status": "queued",
                                      "kind": "investigate", "created_at": time.time() - 300,
                                      "lease_until": 0}
        client.app.state.cases.world.commit(case, case["state_version"], "test", "queue-probe")
        queued = client.get("/v1/operations", headers={"Authorization": "Bearer ops-admin"}).json()
        assert queued["jobs_by_status"] == {"queued": 1}
        assert queued["oldest_queued_age_s"] >= 300
        assert queued["queue_attention"] is True
