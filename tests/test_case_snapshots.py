from copy import deepcopy
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from intentseal_core.policy import AgentPolicy
from intentseal_gateway.cases.fixtures import fixture
from intentseal_gateway.cases.models import CreateCase
from intentseal_gateway.cases.replay import run_scenario
from intentseal_gateway.cases.snapshots import ReplayCapture


def capture_input():
    f = fixture("supplier-contact", "research-agent", "default")
    result = run_scenario(AgentPolicy.model_validate(f["policy"]), f["scenarios"][0])
    return {"agent_id": "research-agent", "task": f["task"], "document": f["document"], "policy": f["policy"],
            "approved_recipients": f["reference"]["approved_recipients"],
            "action": {"event_id": result["decision_event_id"], "tool": "send_message", "args": f["scenarios"][0]["args"], "enforced": "ALLOW"},
            "receipt": result["application_receipt"], "source_locator": "test:instrumented-application", "source_version": "capture-v1",
            "captured_at": datetime.now(timezone.utc).isoformat(), "model_refs": ["scripted-producer:test-double"],
            "tool_build_ref": "local-outbox-v1-test", "scenarios": f["scenarios"]}


def test_capture_freezes_originals_and_remains_scoped(tv_service, monkeypatch):
    body = ReplayCapture.model_validate(capture_input())
    sid, frozen = tv_service.snapshots.capture(body, "default")
    assert tv_service.snapshots.capture(body, "default")[0] == sid
    case = tv_service.create(CreateCase(agent_id="research-agent", snapshot_id=sid, execution_mode="live",
                                        idempotency_key="captured-originals-001"), "default")
    assert case["fixture_id"] is None and not case["missing_evidence"]
    assert tv_service.frozen(case) == frozen
    monkeypatch.setattr("intentseal_gateway.cases.service.fixture", lambda *args: (_ for _ in ()).throw(AssertionError("must use the captured manifest")))
    records = tv_service.source_records(case)
    assert len(records) == 7
    receipt = next(r for r in records if r.kind == "receipt")
    assert receipt.payload["receipt_id"] == body.receipt.receipt_id
    assert all(r.source_version == "capture-v1" for r in records)
    with pytest.raises(KeyError):
        tv_service.snapshots.load(sid, "foreign", "research-agent")
    with pytest.raises(ValueError, match="scope"):
        tv_service.snapshots.capture(body, "foreign")


def test_capture_rejects_missing_or_mismatched_originals():
    value = capture_input()
    bad = deepcopy(value)
    bad["receipt"]["event_id"] = "different-event"
    with pytest.raises(ValidationError):
        ReplayCapture.model_validate(bad)
    bad = deepcopy(value)
    bad["scenarios"][0]["allowed"] = True
    with pytest.raises(ValidationError):
        ReplayCapture.model_validate(bad)
    bad = deepcopy(value)
    bad["scenarios"][0]["tool"] = "shell"
    with pytest.raises(ValidationError):
        ReplayCapture.model_validate(bad)
    bad = deepcopy(value)
    bad["scenarios"][0]["document"] = "different original"
    with pytest.raises(ValidationError):
        ReplayCapture.model_validate(bad)
    bad = deepcopy(value)
    next(s for s in bad["scenarios"] if s["category"] == "utility" and s["tool"] == "send_message")["args"]["body"] = "arbitrary prose"
    with pytest.raises(ValidationError):
        ReplayCapture.model_validate(bad)


def test_capture_api_requires_reviewer_and_preserves_agent_scope(tv_engine, monkeypatch):
    from fastapi.testclient import TestClient
    from intentseal_gateway.app import create_app
    from intentseal_gateway.security import Principal
    monkeypatch.setenv("INTENTSEAL_API_KEYS", "reviewer:admin-test:admin:default,developer:project-test:project:default")
    with TestClient(create_app(tv_engine)) as client:
        value = capture_input()
        assert client.post("/v1/replay-snapshots", json=value).status_code == 401
        assert client.post("/v1/replay-snapshots", json=value,
                           headers={"Authorization": "Bearer project-test"}).status_code == 403
        client.app.state.keys.add("foreign-reviewer", Principal("foreign", "admin", "foreign"))
        assert client.post("/v1/replay-snapshots", json=value,
                           headers={"Authorization": "Bearer foreign-reviewer"}).status_code == 404
        response = client.post("/v1/replay-snapshots", json=value,
                               headers={"Authorization": "Bearer admin-test"})
        assert response.status_code == 201
        assert response.json()["scenario_count"] == 20
        assert "scenarios" not in response.json()


async def test_replay_build_change_blocks_validation(tv_service, tv_request, monkeypatch):
    from intentseal_gateway.cases.world_state import Conflict
    case = tv_service.create(tv_request, "default")
    await tv_service.investigate(case)
    case = tv_service.world.load(case["case_id"], "default")
    monkeypatch.setattr("intentseal_gateway.cases.service.replay_build_sha256", lambda: "changed")
    with pytest.raises(Conflict, match="executor build changed"):
        await tv_service.validate(case, case["candidates"][0]["candidate_id"])
