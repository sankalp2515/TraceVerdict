import pytest

from intentseal_gateway.cases.models import Claim, digest
from intentseal_gateway.cases.repository import evidence, execution_state, graph, ingest, validate_claims
from intentseal_gateway.cases.world_state import Conflict


@pytest.mark.parametrize("fixture_id", ["supplier-contact", "invoice-forward", "report-notify"])
async def test_case_investigates_with_genuine_sample_revision(tv_service, tv_request, fixture_id):
    req = tv_request.model_copy(update={"fixture_id": fixture_id})
    case = tv_service.create(req, "default")
    await tv_service.investigate(case)
    case = tv_service.world.load(case["case_id"], "default")
    assert case["status"] == "PROPOSING" and case["revisions"] == 1
    assert case["critique_history"][0]["disputed_claim_ids"] == ["influence"]
    assert case["critique_history"][1]["disputed_claim_ids"] == []
    assert case["model_calls"] == [] and "deterministic" in case["sample_label"]
    assert not validate_claims(case, case["claims"])
    g = graph(case)
    assert any(e["style"] == "dashed" for e in g["edges"])
    for edge in g["edges"]:
        assert all(eid in case["entities"] for eid in edge["support_evidence_ids"])


def test_case_intake_idempotency_and_tenant_isolation(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    assert case == tv_service.create(tv_request, "default")
    with pytest.raises(Conflict):
        tv_service.create(tv_request.model_copy(update={"fixture_id": "invoice-forward"}), "default")
    with pytest.raises(KeyError):
        tv_service.world.load(case["case_id"], "another-tenant")
    foreign = evidence({**case, "tenant_id": "another-tenant"}, "document", {"text": "hidden"}, "foreign")
    with pytest.raises(ValueError, match="scope"):
        ingest(case, [foreign])


def test_hash_tampering_and_invalid_claim_rejected(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    record = evidence(case, "document", {"text": "original"}, "source")
    with pytest.raises(ValueError, match="hash"):
        ingest(case, [record.model_copy(update={"payload": {"text": "changed"}})])
    claim = Claim(claim_id="invalid", statement="unsupported", support_evidence_ids=["foreign"], basis="observed")
    assert validate_claims(case, [claim.model_dump()])


@pytest.mark.parametrize("action, receipt, expected", [
    ({"enforced": "BLOCK"}, None, "withheld"),
    ({"enforced": "ALLOW"}, None, "allowed-but-unconfirmed"),
    ({"enforced": "ALLOW"}, {"executed": True}, "application-reported-executed"),
    ({"enforced": "BLOCK"}, {"executed": True}, "contradiction"),
])
def test_execution_evidence_states(action, receipt, expected):
    assert execution_state(action, receipt) == expected


def test_exported_records_stable_for_registration(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    a, b = tv_service.source_records(case), tv_service.source_records(case)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]
    assert all(r.content_sha256 == digest(r.payload) for r in a)
