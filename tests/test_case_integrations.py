import json

import httpx
import pytest

from intentseal_core.config import load_settings
from intentseal_gateway.cases.integrations import IntegrationUnavailable, Nightshift, Zetaris
from intentseal_gateway.cases.repository import evidence


def test_live_runtime_configuration_is_pinned(tv_service, tv_request, monkeypatch):
    monkeypatch.setenv("METERLESS_MODEL", "nvidia/primary-model")
    monkeypatch.setenv("METERLESS_REPLAY_MODEL", "nvidia/replay-model")
    case = tv_service.create(tv_request.model_copy(update={"execution_mode": "live"}), "default")
    tv_service.assert_runtime(case)
    profile = case["snapshots"]["inference_runtime"]
    assert profile["primary_route"] == "nvidia/primary-model"
    assert profile["replay_route"] == "nvidia/replay-model"
    monkeypatch.setenv("METERLESS_REPLAY_MODEL", "nvidia/changed-model")
    from intentseal_gateway.cases.world_state import Conflict
    with pytest.raises(Conflict, match="runtime changed"):
        tv_service.assert_runtime(case)


async def test_explicit_replay_model_uses_same_nightshift_transport(monkeypatch):
    for k, v in {"METERLESS_BASE_URL": "https://nightshift.example/v1", "METERLESS_RUNTIME_TOKEN": "private-token",
                 "METERLESS_MODEL": "nvidia/primary-model", "METERLESS_REPLAY_MODEL": "nvidia/replay-model"}.items():
        monkeypatch.setenv(k, v)
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"id": "r1", "model": "returned-replay-model", "choices": [{"message": {"content": "done"}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        _, receipt = await Nightshift(client).call("replay-agent", [{"role": "user", "content": "task"}])
    assert json.loads(seen[0].content)["model"] == "nvidia/replay-model"
    assert str(seen[0].url) == "https://nightshift.example/v1/chat/completions"
    assert receipt["requested_route"] == "nvidia/replay-model"
    assert receipt["actual_model_evidence"] == "returned-replay-model"


async def test_live_mode_missing_credentials_is_incomplete(tv_service, tv_request, monkeypatch):
    for key in ("ZETARIS_REST_URL", "ZETARIS_API_KEY", "ZETARIS_ORG_ID"):
        monkeypatch.delenv(key, raising=False)
    case = tv_service.create(tv_request.model_copy(update={"execution_mode": "live"}), "default")
    job = tv_service.job(case, "investigate", "missing-creds-job")
    import asyncio
    await asyncio.gather(*list(tv_service.tasks))
    result = tv_service.world.load(case["case_id"], "default")
    assert result["status"] == "INCOMPLETE"
    assert result["jobs"][job["job_id"]]["status"] == "incomplete"
    assert not result["candidates"] and not result["model_calls"]


async def test_zetaris_scope_query_receipt_and_response_contract(tv_service, tv_request, monkeypatch):
    case = tv_service.create(tv_request, "default")
    record = evidence(case, "document", {"text": "data"}, "source")
    seen = []
    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"data": [[record.model_dump_json()]]})
    monkeypatch.setenv("ZETARIS_REST_URL", "https://zetaris.example/api/v1.0")
    monkeypatch.setenv("ZETARIS_API_KEY", "private-test-zetaris-token")
    monkeypatch.setenv("ZETARIS_ORG_ID", "7")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await Zetaris(client).read(case, "document")
    request = seen[0]
    assert request.headers["x-org-id"] == "7" and request.headers["x-request-id"]
    sql = json.loads(request.content)["sql"]
    assert "tenant_id='default'" in sql and case["case_id"] in sql and "LIMIT 100" in sql
    assert results[0].query_receipt["execution_mode"] == "live"
    assert "private-test" not in json.dumps(results[0].model_dump())


async def test_zetaris_rejects_cross_case_rows(tv_service, tv_request, monkeypatch):
    case = tv_service.create(tv_request, "default")
    record = evidence({**case, "tenant_id": "other"}, "document", {"text": "secret"}, "source")
    for k, v in {"ZETARIS_REST_URL": "https://zetaris.example", "ZETARIS_API_KEY": "test-token", "ZETARIS_ORG_ID": "1"}.items():
        monkeypatch.setenv(k, v)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={
            "rows": [{"evidence_json": record.model_dump_json()}]}))) as client:
        with pytest.raises(ValueError, match="scope"):
            await Zetaris(client).read(case)


async def test_nightshift_uses_runtime_headers_and_actual_attribution(monkeypatch):
    for k, v in {"METERLESS_BASE_URL": "https://nightshift.example/v1", "METERLESS_RUNTIME_TOKEN": "private-runtime-token",
                 "METERLESS_MODEL": "meterless/test-route"}.items():
        monkeypatch.setenv(k, v)
    seen = []
    def handler(request):
        seen.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "meterless/test-route"}]})
        return httpx.Response(200, json={"id": "response-1", "model": "nvidia/test-concrete-model", "provider": "nvidia",
            "choices": [{"message": {"content": "", "tool_calls": [{"id": "one", "type": "function",
                "function": {"name": "read", "arguments": "{}"}}]}, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = Nightshift(client)
        assert (await adapter.discover())[0]["id"] == "meterless/test-route"
        result, receipt = await adapter.call("investigator", [{"role": "user", "content": "test"}])
    assert result["tool_calls"] and receipt["response_id"] == "response-1"
    assert receipt["requested_route"] != receipt["actual_model_evidence"]
    assert all(r.headers["meterless-app"] == "traceverdict" and r.headers["meterless-scope"] == "user" for r in seen)
    assert "private-runtime-token" not in json.dumps(receipt)


def test_nightshift_only_profile_overrides_all_roles(monkeypatch):
    # A developer's private .env must not refill a deliberately removed test setting.
    monkeypatch.setattr("intentseal_core.config.load_env", lambda: None)
    monkeypatch.setenv("TRACEVERDICT_NIGHTSHIFT_ONLY", "true")
    monkeypatch.setenv("METERLESS_BASE_URL", "https://nightshift.example/v1")
    monkeypatch.setenv("METERLESS_RUNTIME_TOKEN", "test-profile-token")
    monkeypatch.setenv("METERLESS_MODEL", "meterless/discovered")
    settings = load_settings()
    assert set(settings.providers) == {"nightshift"}
    assert "investigator" in settings.roles
    assert all(m.provider == "nightshift" for r in settings.roles.values() for m in r.models)
    monkeypatch.delenv("METERLESS_MODEL")
    with pytest.raises(ValueError, match="Nightshift-only"):
        load_settings()


async def test_live_adapters_do_not_hide_service_failure(tv_service, tv_request, monkeypatch):
    for k, v in {"ZETARIS_REST_URL": "https://zetaris.example", "ZETARIS_API_KEY": "test-token", "ZETARIS_ORG_ID": "1"}.items():
        monkeypatch.setenv(k, v)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        with pytest.raises(IntegrationUnavailable):
            await Zetaris(client).read(tv_service.create(tv_request, "default"))


@pytest.mark.parametrize("critic_disputes", [True, False])
async def test_live_workflow_contract_with_mocked_sponsors(tv_engine, tv_request, monkeypatch, critic_disputes):
    from intentseal_gateway.cases.service import CaseService
    for k, v in {"ZETARIS_REST_URL": "https://zetaris.example/api/v1.0", "ZETARIS_API_KEY": "test-token",
                 "ZETARIS_ORG_ID": "1", "METERLESS_BASE_URL": "https://nightshift.example/v1",
                 "METERLESS_RUNTIME_TOKEN": "test-runtime-token", "METERLESS_MODEL": "meterless/test"}.items():
        monkeypatch.setenv(k, v)
    counter = {"investigator": 0, "critic": 0}
    records, case, model_requests = [], None, []
    def handler(request):
        if request.url.host == "zetaris.example":
            return httpx.Response(200, json={"data": [[r.model_dump_json()] for r in records]})
        body = json.loads(request.content)
        model_requests.append(body)
        tool = body["tools"][0]["function"]["name"]
        if tool in ("retrieve_evidence", "submit_explanation"):
            counter["investigator"] += 1
            rid = next(r.evidence_id for r in records if r.kind == "receipt")
            args = {"claims": [{"claim_id": "execution", "statement": "The sandbox reports execution.",
                    "support_evidence_ids": [rid], "basis": "observed", "competing_explanations": [],
                    "missing_evidence": ["independent attestation"] if not critic_disputes and counter["investigator"] == 1 else [],
                    "review_status": "proposed"}], "uncertainty": []}
            name = "submit_explanation"
        elif tool == "submit_critique":
            counter["critic"] += 1
            rid = next(r.evidence_id for r in records if r.kind == "receipt")
            args = {"checks": [{"claim_id": "execution", "outcome": "uncertain" if critic_disputes and counter["critic"] == 1 else "supported",
                                 "support_evidence_ids": [rid], "reason": "Inspect the recorded receipt and corresponding policy."}],
                    "reason": "Inspect the corresponding policy before accepting the interpretation."}
            name = "submit_critique"
        else:
            name = "propose_repair"
            args = {"operations": [{"path": "contract.mode", "value": "enforce"}],
                    "rationale_claim_ids": ["execution"], "expected_control_effect": "Enforce user intent."}
        return httpx.Response(200, json={"id": "mock-response", "model": "mock-concrete-model",
            "choices": [{"message": {"content": None, "tool_calls": [{"id": "call1", "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)}}]}, "finish_reason": "tool_calls"}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        svc = CaseService(tv_engine, client=client)
        try:
            case = svc.create(tv_request.model_copy(update={"execution_mode": "live"}), "default")
            records = svc.source_records(case)
            await svc.investigate(case)
            result = svc.world.load(case["case_id"], "default")
            assert result["status"] == "PROPOSING" and result["revisions"] == 1
            assert counter == {"investigator": 2, "critic": 2}
            assert len(result["model_calls"]) == 5
            if not critic_disputes:
                assert "execution: unresolved evidence" in json.dumps(model_requests[2])
                assert result["claim_validation_errors"] == []
            assert all(r["query_receipt"] for r in result["entities"].values())
            assert "Read the attachment without replying" not in json.dumps(model_requests)
        finally:
            await svc.close()
