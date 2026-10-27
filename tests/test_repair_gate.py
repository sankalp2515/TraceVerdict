from copy import deepcopy

import pytest
from pydantic import ValidationError

from intentseal_gateway.cases.fixtures import fixture
from intentseal_gateway.cases.models import ApprovalRequest, CandidateRequest, Operation
from intentseal_gateway.cases.replay import gate_report, patched_policy
from intentseal_gateway.cases.world_state import Conflict


async def validated(service, req):
    case = service.create(req, "default")
    await service.investigate(case)
    case = service.world.load(case["case_id"], "default")
    for candidate in case["candidates"]:
        await service.validate(service.world.load(case["case_id"], "default"), candidate["candidate_id"])
    return service.world.load(case["case_id"], "default")


async def test_disruptive_repair_rejected_targeted_control_passes(tv_service, tv_request):
    case = await validated(tv_service, tv_request)
    broad, targeted = [case["validations"][c["candidate_id"]] for c in case["candidates"]]
    assert broad["status"] == "REJECTED" and broad["baseline_reproduced"]
    assert next(o for o in broad["outcomes"] if o["scenario_id"] == "authorized-send")["outcome"] == "fail"
    assert targeted["status"] == "AWAITING_REVIEW" and targeted["counts"] == {"total": 20, "passed": 20, "failed": 0}
    assert len({o["application_receipt"]["receipt_id"] for o in targeted["outcomes"]}) == 20
    assert all(o["application_receipt"]["outbox_count"] <= 1 for o in targeted["outcomes"])
    assert case["status"] == "AWAITING_REVIEW"


async def test_approval_hash_binding_and_no_apply(tv_service, tv_request):
    case = await validated(tv_service, tv_request)
    broad, targeted = case["candidates"]
    report = case["validations"][targeted["candidate_id"]]
    hashes = {"base_policy_sha256": case["base_policy_sha256"], "patch_sha256": targeted["patch_sha256"],
              "validation_report_sha256": report["report_sha256"]}
    with pytest.raises(Conflict):
        tv_service.approve(case, broad["candidate_id"], hashes, "reviewer")
    with pytest.raises(Conflict):
        tv_service.approve(case, targeted["candidate_id"], {**hashes, "patch_sha256": "stale"}, "reviewer")
    approval = tv_service.approve(case, targeted["candidate_id"], hashes, "reviewer")
    assert approval["applied"] is False and approval["scope"] == "sandbox_export"


def test_frozen_evaluation_family_split():
    f = fixture("supplier-contact", "research-agent", "default")
    dev = [s for s in f["scenarios"] if s["category"] == "unsafe" and s["split"] == "development"]
    heldout = [s for s in f["scenarios"] if s["category"] == "unsafe" and s["split"] == "acceptance"]
    assert len(dev) == len(heldout) == 6
    assert len([s for s in f["scenarios"] if s["category"] == "utility"]) == 8
    assert {s["family"] for s in dev}.isdisjoint({s["family"] for s in heldout})


async def test_missing_outcome_or_receipt_cannot_pass(tv_service, tv_request):
    case = await validated(tv_service, tv_request)
    candidate = case["candidates"][1]
    report = case["validations"][candidate["candidate_id"]]
    f = fixture(case["fixture_id"], case["agent_id"], case["tenant_id"])
    assert gate_report(candidate, f, report["baseline"], report["outcomes"][:-1])["status"] == "INCOMPLETE"
    outcomes = deepcopy(report["outcomes"])
    outcomes[0]["application_receipt"] = None
    assert gate_report(candidate, f, report["baseline"], outcomes)["status"] == "INCOMPLETE"
    forged = deepcopy(report["outcomes"])
    forged[0]["application_receipt"]["executed"] = True
    forged[0]["application_receipt"]["outbox_count"] = 1
    forged[0]["outcome"] = "pass"
    assert gate_report(candidate, f, report["baseline"], forged)["status"] == "REJECTED"


def test_strict_and_allowlisted_patch_contract(tv_service, tv_request):
    with pytest.raises(ValidationError):
        Operation(path="logging.enabled", value="enforce")
    with pytest.raises(ValidationError):
        ApprovalRequest(base_policy_sha256="a", patch_sha256="b", validation_report_sha256="c", reviewer="spoof")
    f = fixture("supplier-contact", "research-agent", "default")
    req = CandidateRequest(operations=[Operation(path="tools.send_message.allowed_recipients", value=["evil@elsewhere.test"])],
                           rationale_claim_ids=["x"], expected_control_effect="bad")
    with pytest.raises(ValueError, match="directory"):
        patched_policy(f["policy"], req, f["reference"]["approved_recipients"])
