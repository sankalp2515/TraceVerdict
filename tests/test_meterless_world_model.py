from copy import deepcopy

import pytest

from intentseal_gateway.cases.world_model import WorldModel, entity_id_from_name, normalize_name


def test_case_context_uses_rebuilt_engine_state(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    records = tv_service.source_records(case)
    case = tv_service.ingest_records(case, records)
    events = deepcopy(case["world_model"]["events"])
    case = tv_service.ingest_records(case, records)
    assert case["world_model"]["events"] == events
    context = tv_service.world.context(case, "critic")
    assert {r["evidence_id"] for r in context["entities"]} == set(case["entities"])
    assert all(r["selection_reason"].startswith("world_model") for r in context["entities"])
    assert len(WorldModel("rebuild", deepcopy(case["world_model"])).evidence_records()) == 7


def test_full_context_budget_and_append_integrity(tv_service, tv_request):
    case = tv_service.create(tv_request, "default")
    case = tv_service.ingest_records(case, tv_service.source_records(case))
    with pytest.raises(ValueError, match="budget"):
        tv_service.world.context(case, "critic", budget_chars=10)
    case["world_model"]["events"][0]["kind"] = "tamper"
    with pytest.raises(ValueError, match="history"):
        tv_service.world.commit(case, case["state_version"], "attacker", "tamper")


def test_name_identity_and_provenance():
    assert normalize_name(" José\u00a0 García ") == "jose garcia"
    assert entity_id_from_name("person", "José García") == entity_id_from_name("person", "jose garcia")
    world = WorldModel("test")
    with pytest.raises(ValueError, match="provenance"):
        world.upsert_entity({"type": "claim", "name": "untrusted"})
