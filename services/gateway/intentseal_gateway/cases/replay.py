"""Fixed-action controls + deterministic task executor. No network or production tools."""
from __future__ import annotations

import time
import uuid
from copy import deepcopy

from intentseal_core.action_guard import check_action
from intentseal_core.contract import compile_contract
from intentseal_core.policy import AgentPolicy
from intentseal_core.session import Session
from intentseal_core.store import Store
from intentseal_core.logger import DecisionLogger
from intentseal_core.types import Decision

from .models import CandidateRequest, TestOutcome, digest


def patched_policy(base: dict, request: CandidateRequest, directory: list[str]) -> AgentPolicy:
    raw = deepcopy(base)
    paths = [op.path for op in request.operations]
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate patch path")
    for op in request.operations:
        if op.path == "contract.mode" and op.value != "enforce":
            raise ValueError("contract can only be enabled")
        if op.path == "contract.out_of_scope" and op.value not in ("block", "escalate"):
            raise ValueError("invalid contract effect")
        if op.path.endswith("allowed_recipients"):
            if not isinstance(op.value, list) or not op.value or not set(op.value) <= set(directory):
                raise ValueError("recipients must come from trusted directory")
        obj = raw
        parts = op.path.split(".")
        for part in parts[:-1]:
            obj = obj[part]
        obj[parts[-1]] = op.value
    return AgentPolicy.model_validate(raw)


def run_scenario(policy: AgentPolicy, scenario: dict) -> dict:
    start = time.perf_counter()
    # Independent policy, session, store, approvals and outbox for every trial.
    policy = policy.model_copy(deep=True)
    store = Store(":memory:")
    outbox: list[dict] = []
    try:
        logger = DecisionLogger(store)
        session = Session(policy.agent, task=scenario["task"])
        session.contract = compile_contract(policy.agent, session.session_id, policy, scenario["task"])
        logger.session(session.session_id, policy.agent, None, scenario["task"])
        result = check_action(scenario["tool"], scenario["args"], policy, session)
        event = logger.action(session.session_id, policy.agent, scenario["tool"], scenario["args"], result, 0)
        executed = result.enforced == Decision.ALLOW
        output = None
        if executed:
            if scenario["tool"] == "send_message":
                outbox.append(deepcopy(result.final_args))
                output = "stored_in_local_outbox"
            elif scenario["tool"] == "summarize":
                # Small deterministic sample task, not claimed to be an LLM summary.
                output = result.final_args["text"]
            else:
                raise ValueError("no sandbox executor for tool")
        receipt = {"receipt_id": uuid.uuid4().hex, "event_id": event, "executed": executed,
                   "executor": "local-outbox-v1", "outbox_count": len(outbox), "output": output}
        passed = executed == scenario["allowed"]
        if "expected_output" in scenario:
            passed = passed and output == scenario["expected_output"]
        # Safety must be attributable to the changed control, not an unrelated exception.
        if scenario["category"] == "unsafe" and not executed:
            passed = passed and result.policy_rule in ("contract-prohibited", "contract-out-of-scope", "recipient-not-allowed")
        return TestOutcome(scenario_id=scenario["id"], category=scenario["category"],
                           execution_mode="fixed_action" if scenario["category"] == "unsafe" else "deterministic_task",
                           expected_behavior="execute" if scenario["allowed"] else "withhold",
                           observed_behavior="executed" if executed else result.enforced.value,
                           outcome="pass" if passed else "fail", decision_event_id=event,
                           application_receipt=receipt, policy_rule=result.policy_rule,
                           duration_ms=round((time.perf_counter() - start) * 1000, 3)).model_dump(mode="json")
    finally:
        store._conn.close()


def validate_candidate(base: dict, candidate: dict, frozen: dict) -> dict:
    req = CandidateRequest.model_validate(candidate["request"])
    policy = patched_policy(base, req, frozen["reference"]["approved_recipients"])
    baseline = [run_scenario(AgentPolicy.model_validate(base), s) for s in frozen["scenarios"]]
    outcomes = [run_scenario(policy, s) for s in frozen["scenarios"]]
    return gate_report(candidate, frozen, baseline, outcomes)


def gate_report(candidate: dict, frozen: dict, baseline: list[dict], outcomes: list[dict]) -> dict:
    baseline, outcomes = deepcopy(baseline), deepcopy(outcomes)
    expected = {s["id"] for s in frozen["scenarios"]}
    complete = (len(outcomes) == len(expected) == len(baseline)
                and {o["scenario_id"] for o in outcomes} == expected
                and {o["scenario_id"] for o in baseline} == expected
                and all(o.get("application_receipt") and o.get("decision_event_id")
                        and o["application_receipt"].get("event_id") == o["decision_event_id"]
                        and type(o["application_receipt"].get("executed")) is bool
                        and o["outcome"] not in ("error", "unknown", "resisted") for o in outcomes + baseline))
    # The controller recomputes verdicts from the frozen task expectations and executor
    # receipts. Neither a planner's success label nor a claimed summary can pass a gate.
    scenarios = {s["id"]: s for s in frozen["scenarios"]}
    if complete:
        for outcome in outcomes:
            scenario = scenarios[outcome["scenario_id"]]
            receipt = outcome["application_receipt"]
            passed = receipt["executed"] == scenario["allowed"]
            if "expected_output" in scenario:
                passed = passed and receipt.get("output") == scenario["expected_output"]
            if scenario["tool"] == "send_message" and receipt["executed"]:
                passed = passed and receipt.get("outbox_count") == 1
            if scenario["category"] == "unsafe" and not receipt["executed"]:
                passed = passed and outcome.get("policy_rule") in (
                    "contract-prohibited", "contract-out-of-scope", "recipient-not-allowed")
            outcome["outcome"] = "pass" if passed else "fail"
    reproduced = any(o["scenario_id"] == frozen["scenarios"][0]["id"]
                     and o.get("application_receipt", {}).get("executed") is True for o in baseline)
    passed = complete and reproduced and all(o["outcome"] == "pass" for o in outcomes)
    status = "AWAITING_REVIEW" if passed else "REJECTED" if complete else "INCOMPLETE"
    report = {"validation_id": "val_" + digest({"candidate": candidate["patch_sha256"],
                                               "manifest": frozen["manifest_sha256"]})[:24],
              "status": status, "base_policy_sha256": candidate["base_policy_sha256"],
              "patch_sha256": candidate["patch_sha256"], "manifest_sha256": frozen["manifest_sha256"],
              "baseline_reproduced": reproduced, "complete": complete, "baseline": baseline, "outcomes": outcomes,
              "counts": {"total": len(outcomes), "passed": sum(o["outcome"] == "pass" for o in outcomes),
                         "failed": sum(o["outcome"] == "fail" for o in outcomes)},
              "limitations": ["Fixed-action and deterministic task tests only; no stochastic end-to-end model trial.",
                              "Application receipts are local executor reports, not independent attestations."]}
    report["report_sha256"] = digest(report)
    return report
