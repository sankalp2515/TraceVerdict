import time

from fastapi.testclient import TestClient

from intentseal_gateway.app import create_app
from intentseal_gateway.security import Principal


def test_authenticated_case_workflow_and_graph(tv_engine, tv_request, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "reviewer:admin-test:admin:default,developer:project-test:project:default")
    app = create_app(tv_engine)
    with TestClient(app) as client:
        app.state.keys.add("foreign-key", Principal("foreign", "project", "another-tenant"))
        req = tv_request.model_dump(mode="json")
        assert client.post("/v1/cases", json=req).status_code == 401
        headers = {"Authorization": "Bearer project-test"}
        r = client.post("/v1/cases", json=req, headers=headers)
        assert r.status_code == 201, r.text
        cid = r.json()["case_id"]
        assert client.get(f"/v1/cases/{cid}", headers={"Authorization": "Bearer foreign-key"}).status_code == 404
        assert client.post(f"/v1/cases/{cid}/investigate", json={"idempotency_key": "run-case-001"}, headers=headers).status_code == 202
        for _ in range(200):
            case = client.get(f"/v1/cases/{cid}", headers=headers).json()
            if case["status"] in ("PROPOSING", "INCOMPLETE") and all(j["status"] != "running" for j in case["jobs"].values()):
                break
            time.sleep(.01)
        assert case["status"] == "PROPOSING", case
        graph = client.get(f"/v1/cases/{cid}/graph", headers=headers).json()
        assert graph["nodes"] and graph["edges"]
        eid = next(iter(case["entities"]))
        assert client.get(f"/v1/cases/{cid}/evidence/{eid}", headers=headers).status_code == 200
        assert client.get(f"/v1/cases/{cid}/evidence/foreign", headers=headers).status_code == 404
        assert client.get(f"/v1/cases/{cid}/source-records", headers=headers).status_code == 403
        for i, candidate in enumerate(case["candidates"]):
            rid = candidate["candidate_id"]
            assert client.post(f"/v1/repairs/{rid}/validate", json={"idempotency_key": f"validation-{i}"}, headers=headers).status_code == 202
            for _ in range(200):
                case = client.get(f"/v1/cases/{cid}", headers=headers).json()
                if rid in case["validations"] and all(j["status"] not in ("queued", "running") for j in case["jobs"].values()):
                    break
                time.sleep(.01)
            assert rid in case["validations"]
        targeted = case["candidates"][1]
        report = case["validations"][targeted["candidate_id"]]
        assert client.get(f"/v1/validations/{report['validation_id']}", headers=headers).status_code == 200
        hashes = {"base_policy_sha256": case["base_policy_sha256"], "patch_sha256": targeted["patch_sha256"],
                  "validation_report_sha256": report["report_sha256"]}
        url = f"/v1/repairs/{targeted['candidate_id']}/approve"
        assert client.post(url, json=hashes, headers=headers).status_code == 403
        approved = client.post(url, json=hashes, headers={"Authorization": "Bearer admin-test"})
        assert approved.status_code == 200, approved.text
        assert approved.json()["reviewer"] == "reviewer" and approved.json()["applied"] is False
        assert client.post(f"/v1/repairs/{targeted['candidate_id']}/apply", json={}, headers=headers).status_code == 404


def test_sample_server_cannot_expose_dummy_enforcement(tv_request, monkeypatch, tmp_path):
    from intentseal_gateway.cases.sample_app import app
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "developer:sample-test:project:default")
    monkeypatch.setenv("TRACEVERDICT_SAMPLE_DB", str(tmp_path / "sample.db"))
    with TestClient(app) as client:
        headers = {"Authorization": "Bearer sample-test"}
        body = tv_request.model_dump(mode="json")
        assert client.post("/v1/cases", json=body, headers=headers).status_code == 201
        body["execution_mode"] = "live"
        assert client.post("/v1/cases", json=body, headers=headers).status_code == 422
        paths = client.get("/openapi.json").json()["paths"]
        assert "/v1/inspect" not in paths and "/v1/chat/completions" not in paths
