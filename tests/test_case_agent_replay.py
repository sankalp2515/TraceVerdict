import json

import pytest

from intentseal_core.policy import AgentPolicy
from intentseal_gateway.cases.agent_replay import run_agent_trial, run_agent_suite
from intentseal_gateway.cases.fixtures import fixture


class ScriptedModels:
    """A test double, never used by the application's live path."""
    def __init__(self, name, args):
        self.name, self.args, self.calls = name, args, 0

    async def call(self, role, messages, tools):
        self.calls += 1
        calls = [] if self.calls > 1 else [{"id": "one", "type": "function", "function": {
            "name": "choose_action", "arguments": json.dumps({"action": self.name, "recipient": self.args.get("to", "")})}}]
        return {"content": "done", "tool_calls": calls}, {"execution_mode": "test_double", "requested_route": "scripted"}


async def test_model_attempt_is_separate_from_control_effect():
    f = fixture("supplier-contact", "agent", "default")
    scenario = f["scenarios"][0]
    base = AgentPolicy.model_validate(f["policy"])
    baseline = await run_agent_trial(ScriptedModels(scenario["tool"], scenario["args"]), base, scenario, f["document"])
    assert baseline["outcome"] == "fail" and baseline["outbox_count"] == 1
    base.contract.mode = "enforce"
    candidate = await run_agent_trial(ScriptedModels(scenario["tool"], scenario["args"]), base, scenario, f["document"])
    assert candidate["outcome"] == "pass" and candidate["outbox_count"] == 0
    assert candidate["actions"][0]["rule"] == "contract-prohibited"


async def test_model_resistance_is_not_a_control_pass():
    f = fixture("supplier-contact", "agent", "default")
    models = ScriptedModels("send_message", {})
    models.calls = 1
    result = await run_agent_trial(models, AgentPolicy.model_validate(f["policy"]), f["scenarios"][0], f["document"])
    assert result["outcome"] == "resisted" and not result["actions"]


@pytest.mark.parametrize("index", [3, 4, 5])
async def test_model_utility_requires_actual_local_artifact(index):
    f = fixture("supplier-contact", "agent", "default")
    scenario = f["scenarios"][index]
    arguments = {"source_id": "document"} if scenario["tool"] == "summarize" else scenario["args"]
    result = await run_agent_trial(ScriptedModels(scenario["tool"], arguments),
                                   AgentPolicy.model_validate(f["policy"]), scenario, f["document"])
    assert result["outcome"] == "pass"
    assert result["actions"][0]["executed"] is True


async def test_model_cannot_request_external_executor():
    f = fixture("supplier-contact", "agent", "default")
    with pytest.raises(ValueError, match="sandbox"):
        await run_agent_trial(ScriptedModels("shell", {"command": "no"}),
                              AgentPolicy.model_validate(f["policy"]), f["scenarios"][0], f["document"])


async def test_invalid_trial_retained_without_losing_remaining_results():
    f = fixture("supplier-contact", "agent", "default")
    outcomes = await run_agent_suite(ScriptedModels("shell", {"command": "no"}),
                                     AgentPolicy.model_validate(f["policy"]), f)
    assert len(outcomes) == len(f["scenarios"])
    assert outcomes[0]["outcome"] == "error"
    assert outcomes[0]["error_code"] == "ValueError"
    assert all(o["outcome"] != "pass" for o in outcomes)


async def test_read_cannot_smuggle_a_recipient():
    f = fixture("supplier-contact", "agent", "default")
    scenario = next(s for s in f["scenarios"] if s["tool"] == "summarize")
    with pytest.raises(ValueError, match="invalid sandbox action"):
        await run_agent_trial(ScriptedModels("summarize", {"to": "other@local.test"}),
                              AgentPolicy.model_validate(f["policy"]), scenario, f["document"])
