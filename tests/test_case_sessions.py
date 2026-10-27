from fastapi.testclient import TestClient


def test_browser_session_csrf_scope_and_revocation(tmp_path, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "dev:project-workspace-test-key:project:default")
    monkeypatch.setenv("TRACEVERDICT_DB_URL", str(tmp_path / "sessions.db"))
    monkeypatch.setenv("TRACEVERDICT_COOKIE_SECURE", "false")
    from intentseal_gateway.cases.app import app
    with TestClient(app) as client:
        assert client.get("/v1/cases").status_code == 401
        bad = client.post("/v1/auth/session", json={"api_key": "wrong"})
        assert bad.status_code == 401
        response = client.post("/v1/auth/session", json={"api_key": "project-workspace-test-key"})
        assert response.status_code == 200
        assert "httponly" in response.headers["set-cookie"].lower()
        assert "project-workspace-test-key" not in response.text
        csrf = response.json()["csrf_token"]
        assert client.get("/v1/cases").status_code == 200
        body = {"agent_id": "research-agent", "fixture_id": "supplier-contact", "execution_mode": "sample", "idempotency_key": "browser-case-001"}
        assert client.post("/v1/cases", json=body).status_code == 403
        headers = {"Origin": "http://localhost:5173", "X-CSRF-Token": csrf}
        created = client.post("/v1/cases", json=body, headers=headers)
        assert created.status_code == 201
        assert len(client.get("/v1/cases").json()["items"]) == 1
        assert client.post("/v1/cases", json=body, headers={**headers, "Origin": "https://attacker.invalid"}).status_code == 403
        assert client.get("/v1/cases", headers={"Authorization": "Bearer invalid-explicit-key"}).status_code == 401
        assert client.post("/v1/auth/logout", headers=headers).status_code == 200
        assert client.get("/v1/cases").status_code == 401


def test_sessions_expire_and_credentials_can_be_revoked(tmp_path, monkeypatch):
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "dev:project-workspace-test-key:project:default")
    monkeypatch.setenv("TRACEVERDICT_DB_URL", str(tmp_path / "expiry.db"))
    monkeypatch.setenv("TRACEVERDICT_COOKIE_SECURE", "false")
    from intentseal_gateway.cases.app import app
    with TestClient(app) as client:
        assert client.post("/v1/auth/session", json={"api_key": "project-workspace-test-key"}).status_code == 200
        app.state.engine.store.execute("UPDATE tv_browser_sessions SET expires_at=0")
        assert client.get("/v1/auth/session").status_code == 401
        assert client.post("/v1/auth/session", json={"api_key": "project-workspace-test-key"}).status_code == 200
        app.state.keys._keys.clear()
        assert client.get("/v1/auth/session").status_code == 401
