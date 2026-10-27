import asyncio
from copy import deepcopy

import pytest

from intentseal_gateway.cases.repository import evidence, ingest
from intentseal_gateway.cases.world_state import Conflict, WorldState


def test_stale_writes_and_restart(tv_engine, tv_request):
    state = WorldState(tv_engine.store)
    initial = {"snapshots": {}, "base_policy_sha256": "base", "fixture_id": None,
               "execution_mode": "sample", "session_ids": []}
    first = state.create("one", "default", "research-agent", "req", initial)
    stale = deepcopy(first)
    ingest(first, [evidence(first, "document", {"text": "record"}, "source:1")])
    second = state.commit(first, 0, "investigator", "ingest")
    assert WorldState(tv_engine.store).load("one", "default") == second
    with pytest.raises(Conflict):
        state.commit(stale, 0, "critic", "lost_update")
    second["claims"] = [{"claim_id": "claim", "basis": "inferred"}]
    final = state.commit(second, 1, "critic", "critique")
    assert len(final["entities"]) == 1 and len(final["observations"]) == 2
    assert state.context(final, "critic")["claims"]
    assert final["observations"][1]["parent_sha256"]
    assert state.at_version("one", "default", 1)["claims"] == []
    assert state.at_version("one", "default", 2)["claims"] == final["claims"]


def test_immutable_snapshots_and_invalid_transition(tv_service, tv_request):
    state = tv_service.world
    case = tv_service.create(tv_request, "default")
    case["snapshots"]["policy"]["contract"]["mode"] = "enforce"
    with pytest.raises(Conflict, match="anchor"):
        state.commit(case, 0, "model", "tamper")
    case = state.load(case["case_id"], "default")
    with pytest.raises(Conflict, match="transition"):
        state.commit(case, 0, "model", "approve", "APPROVED")


async def test_job_idempotency_and_worker_recovery(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    first = tv_service.job(case, "investigate", "same-job-key")
    second = tv_service.job(tv_service.world.load(case["case_id"], "default"), "investigate", "same-job-key")
    assert first["job_id"] == second["job_id"]
    await asyncio.gather(*list(tv_service.tasks))
    case = tv_service.world.load(case["case_id"], "default")
    assert case["status"] == "PROPOSING"
    assert len(case["candidates"]) == 2
    assert case["jobs"][first["job_id"]]["status"] == "complete"
    assert not tv_service.active_jobs


async def test_resume_from_critic_state(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    case = await tv_service.fetch(case)
    case = tv_service.world.commit(case, case["state_version"], "controller", "start", "EXPLAINING")
    case, explanation = await tv_service.investigator(case)
    case["claims"] = [c.model_dump(mode="json") for c in explanation.claims]
    case["evidence_calls"] = 1
    case = tv_service.world.commit(case, case["state_version"], "investigator", "submitted", "CRITIQUING")
    await tv_service.investigate(case)
    resumed = tv_service.world.load(case["case_id"], "default")
    assert resumed["status"] == "PROPOSING" and resumed["revisions"] == 1
