from copy import deepcopy

from fastapi.testclient import TestClient

from intentseal_core.store import Store
from intentseal_gateway.cases.onboarding import AgentRegistry, AgentRegistration
from test_case_snapshots import capture_input


def test_registry_is_durable_and_never_overwrites_existing_policy(tmp_path):
    store = Store(tmp_path / "onboarding.db")
    registry = AgentRegistry(store)
    body = AgentRegistration.model_validate({"agent_id": "customer-agent", "policy": {"agent": "customer-agent", "org": "customer"}})
    registry.register(body, "customer")
    assert AgentRegistry(store).load("customer-agent").org == "customer"
    import pytest
    with pytest.raises(FileExistsError):
        registry.register(body, "customer")
    with pytest.raises(ValueError):
        registry.register(body, "foreign")


def test_customer_agent_capture_publication_and_scope(tmp_path, monkeypatch):
    from intentseal_gateway.cases.app import app
    monkeypatch.setenv("TRACEVERDICT_DB_URL", str(tmp_path / "api.db"))
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "owner:review-key:admin:customer,dev:project-key:project:customer,other:foreign-key:admin:foreign")
    monkeypatch.setenv("TRACEVERDICT_MANAGED_SOURCES", "true")
    admin = {"Authorization": "Bearer review-key"}
    project = {"Authorization": "Bearer project-key"}
    foreign = {"Authorization": "Bearer foreign-key"}
    capture = capture_input()
    capture["agent_id"] = capture["policy"]["agent"] = "customer-agent"
    capture["policy"]["org"] = "customer"
    registration = {"agent_id": capture["agent_id"], "policy": capture["policy"]}
    published = []
    def publish(records):
        published.extend(records)
        return [{"source": "events", "records": 4}]
    monkeypatch.setattr("intentseal_gateway.cases.onboarding.publish_records", publish)
    with TestClient(app) as client:
        assert client.post("/v1/agents", json=registration, headers=project).status_code == 403
        assert client.post("/v1/agents", json=registration, headers=foreign).status_code == 422
        assert client.post("/v1/agents", json=registration, headers=admin).status_code == 201
        assert client.post("/v1/agents", json=registration, headers=admin).status_code == 409
        assert "customer-agent" in str(client.get("/v1/agents", headers=project).json())
        assert "customer-agent" not in str(client.get("/v1/agents", headers=foreign).json())
        bad = deepcopy(capture); bad["receipt"]["event_id"] = "wrong-event"
        assert client.post("/v1/replay-snapshots", json=bad, headers=admin).status_code == 422
        response = client.post("/v1/replay-snapshots", json=capture, headers=admin)
        assert response.status_code == 201, response.text
        response = client.post("/v1/cases", json={"agent_id": "customer-agent", "snapshot_id": response.json()["snapshot_id"],
            "execution_mode": "live", "idempotency_key": "customer-original-case"}, headers=project)
        assert response.status_code == 201, response.text
        cid = response.json()["case_id"]
        path = f"/v1/cases/{cid}/publish-source-records"
        assert client.post(path, headers=project).status_code == 403
        assert client.post(path, headers=foreign).status_code == 404
        assert client.post(path, headers=admin).status_code == 200
        assert len(published) == 7 and all(r.tenant_id == "customer" for r in published)
        monkeypatch.setenv("TRACEVERDICT_MANAGED_SOURCES", "false")
        assert client.post(path, headers=admin).status_code == 409
