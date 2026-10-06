"""Engine decision flow and fault injection; benign inputs, no external models."""

from __future__ import annotations

import asyncio
import json
import time

import pytest

from asg_core.decision_model import StaticDecisionModel
from asg_core.engine import Engine
from asg_core.policy import load_policy
from asg_core.store import Store
from asg_core.types import ATTACK_TYPES, Decision

MARKER = "REVIEW_MARKER"
FLAGGED = '<p>Quarterly report ready.</p><span hidden>' + MARKER + '</span>'


class Scorer:
    def __init__(self, score=0.95, error=False):
        self.value, self.error, self.calls = score, error, []

    def score(self, text):
        self.calls.append(text)
        if self.error:
            raise RuntimeError("scorer unavailable")
        return self.value if MARKER in text else 0.0


@pytest.fixture
def policy():
    p = load_policy("research-agent")
    p.sensitive_data.canaries = []
    return p


def engine(policy, malicious=0.0, **kwargs):
    judge = kwargs.pop("decision_model", StaticDecisionModel(malicious))
    return Engine(policy_loader=lambda _: policy, decision_model=judge,
                  classifiers=kwargs.pop("classifiers", [Scorer()]), store=kwargs.pop("store", Store(":memory:")), **kwargs)


async def test_clean_fast_path_unchanged_and_logged(policy):
    e = engine(policy)
    content = "  Quarterly revenue was 4.2 million.\n"
    r = await e.inspect(content, "web", policy.agent)
    assert r.decision == r.enforced == Decision.ALLOW
    # Tier 1 scores all untrusted content (D-019); low scores never reach the judge and change nothing.
    assert r.cleaned_content == content and r.tier == 1 and not r.degraded
    assert e.classifiers[0].calls and e.decision_model.calls == 0
    rows = e.logger.decisions()
    assert len(rows) == 1 and rows[0]["event_id"] == r.event_id and rows[0]["policy_rule"] == "allow"


@pytest.mark.parametrize("source", ["user", "web", "pdf", "email", "markdown", "html", "docx", "api", "ocr_text", "code", "image", "db", "tool"])
async def test_single_entry_for_all_channels(policy, source):
    e = engine(policy)
    r = await e.inspect("The report is ready.", source, policy.agent, fmt="text")
    assert r.decision == Decision.ALLOW and e.logger.decisions()[0]["source"] == source


async def test_hidden_content_quarantined_despite_benign_judge(policy):
    e = engine(policy)
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.decision == Decision.NEUTRALISE and r.policy_rule == "drop-non-visible"
    assert MARKER not in r.cleaned_content and "Quarterly report ready." in r.cleaned_content
    assert "[QUARANTINED]" in r.cleaned_content and "UNTRUSTED-" in r.cleaned_content
    assert r.tier == 2 and e.decision_model.calls == 1
    assert all(f.labels and set(f.labels) <= set(ATTACK_TYPES) for f in r.findings)
    event = e.logger.session_events(e.logger.decisions()[0]["session_id"])[0]
    hidden = next(f for f in event["findings"] if f["signal"] == "non-visible-content")
    assert hidden["span_start"] == 0 and hidden["span_end"] == len(MARKER)


async def test_classifier_is_advice_not_a_decider(policy):
    policy.sensitive_data.drop_non_visible = False
    e = engine(policy, classifiers=[Scorer(1.0)])
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.decision == Decision.ALLOW and r.risk == 0 and not r.degraded
    assert any(f.signal == "classifier" and f.score == 1 for f in r.findings)


async def test_judge_block_and_labels(policy):
    e = engine(policy, decision_model=StaticDecisionModel(0.95, {"Context Poisoning": 0.9, "unknown": 1}))
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.decision == Decision.BLOCK and r.policy_rule == "content-risk-block"
    assert MARKER not in r.cleaned_content and "Context Poisoning" in r.labels and "unknown" not in r.labels


async def test_exact_evidence_preserves_surrounding_text_and_whitespace(policy):
    policy.sensitive_data.drop_non_visible = False
    judge = StaticDecisionModel(0.7)
    judge.result.evidence = [MARKER, MARKER, "absent quote"]
    e = engine(policy, decision_model=judge)
    content = "  First paragraph.\n" + MARKER + "\u200b\nLast paragraph.  "
    r = await e.inspect(content, "web", policy.agent)
    assert r.policy_rule == "judge-neutralise"
    assert "  First paragraph.\n[QUARANTINED]\u200b\nLast paragraph.  " in r.cleaned_content
    findings = [f for f in r.findings if f.signal == "judge"]
    assert len(findings) == 1 and findings[0].preview == MARKER


async def test_transformed_evidence_uses_original_span_fallback(policy):
    policy.sensitive_data.drop_non_visible = False
    judge = StaticDecisionModel(0.7)
    judge.result.evidence = [MARKER]
    e = engine(policy, decision_model=judge)
    content = "REVIEW_\u200bMARKER"
    r = await e.inspect(content, "web", policy.agent)
    assert r.decision == Decision.NEUTRALISE
    assert next(f for f in r.findings if f.signal == "judge").span == (0, len(content))
    assert content not in r.cleaned_content


async def test_original_normalisation_record_and_detected_views(policy):
    e = engine(policy)
    content = "monthly rеport\u200b ready"  # ordinary word with Cyrillic ie
    r = await e.inspect(content, "web", policy.agent)
    assert r.cleaned_content == content and r.risk == 0
    assert any(f.signal.startswith("normalisation:") and "format_chars_removed" in f.signal for f in r.findings)
    assert "monthly report ready" in e.classifiers[0].calls


async def test_encoded_structure_is_only_a_signal(policy):
    e = engine(policy)
    content = "YWJj" * 20  # repeated benign encoded letters, not instructions
    r = await e.inspect(content, "api", policy.agent, fmt="text")
    assert r.decision == Decision.ALLOW and r.cleaned_content == content and r.tier == 2
    assert "Encoded Instructions" in r.labels


async def test_session_accumulation_decay_and_cached_scan(policy):
    policy.sensitive_data.drop_non_visible = False
    e = engine(policy, malicious=0.4)
    s = e.start_session(policy.agent, task="Summarise the report")
    decisions = []
    for _ in range(7):
        decisions.append(await e.inspect(FLAGGED, "web", policy.agent, s.session_id))
    assert decisions[0].decision == Decision.ALLOW
    assert any(r.policy_rule == "session-risk-escalate" for r in decisions)
    assert decisions[-1].policy_rule == "session-risk-block"
    assert s.risk == pytest.approx(1.6) and s.turns == 7
    assert e.decision_model.calls == 1 and len(e.classifiers[0].calls) == 1
    await e.inspect("Ordinary report.", "web", policy.agent, s.session_id)
    assert s.risk == pytest.approx(1.4)


async def test_monitor_and_enforce_same_decision_different_content(policy):
    enforcing = await engine(policy, malicious=0.95).inspect(FLAGGED, "web", policy.agent)
    monitor_policy = policy.model_copy(deep=True)
    monitor_policy.mode = "monitor"
    e = engine(monitor_policy, malicious=0.95)
    monitoring = await e.inspect(FLAGGED, "web", policy.agent)
    assert enforcing.decision == monitoring.decision == Decision.BLOCK
    assert enforcing.risk == monitoring.risk and enforcing.policy_rule == monitoring.policy_rule
    assert monitoring.enforced == Decision.ALLOW and MARKER in monitoring.cleaned_content
    assert e.logger.decisions()[0]["enforced"] == "ALLOW"


async def test_policy_thresholds_are_used_and_current_policy_reapplied(policy):
    policy.sensitive_data.drop_non_visible = False
    e = engine(policy, malicious=0.7)
    assert (await e.inspect(FLAGGED, "web", policy.agent)).policy_rule == "judge-neutralise"
    policy.thresholds.neutralise = 0.75
    assert (await e.inspect(FLAGGED, "web", policy.agent)).decision == Decision.ALLOW
    policy.thresholds.block = 0.65
    assert (await e.inspect(FLAGGED, "web", policy.agent)).policy_rule == "content-risk-block"


@pytest.mark.parametrize("failure", ["degraded", "exception", "timeout", "nan"])
async def test_judge_failures_hold_flagged_content(policy, failure):
    judge = StaticDecisionModel(degraded=failure == "degraded")
    if failure == "exception":
        async def fail(*args):
            raise RuntimeError("unavailable")
        judge.assess = fail
    elif failure == "timeout":
        async def slow(*args):
            await asyncio.sleep(1)
        judge.assess = slow
    elif failure == "nan":
        judge.result.malicious = float("nan")
    e = engine(policy, decision_model=judge, tier2_timeout_s=0.01)
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.decision == Decision.BLOCK and r.degraded and r.policy_rule == "judge-unavailable-hold"
    assert e.logger.decisions()[0]["degraded"] == 1


async def test_classifier_failure_can_be_resolved_by_judge_but_is_logged(policy):
    policy.sensitive_data.drop_non_visible = False
    e = engine(policy, classifiers=[Scorer(error=True)])
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.degraded and r.decision == Decision.ALLOW and e.decision_model.calls == 1


async def test_classifier_timeout_is_bounded(policy):
    class SlowScorer:
        async def score(self, text):
            await asyncio.sleep(1)
    e = engine(policy, classifiers=[SlowScorer()], tier1_timeout_s=0.01)
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.degraded and r.policy_rule == "drop-non-visible"


async def test_extraction_warning_and_timeout_are_held(policy, monkeypatch):
    e = engine(policy)
    r = await e.inspect(b"Ordinary report, not a PDF file", "pdf", policy.agent, fmt="pdf")
    assert r.policy_rule == "extraction-failed" and r.degraded and r.decision == Decision.BLOCK
    def slow(*args):
        time.sleep(0.02)
        raise RuntimeError("unavailable")
    monkeypatch.setattr(e, "_scan", slow)
    e.tier0_timeout_s = 0.001
    r = await e.inspect("Another report.", "web", policy.agent)
    assert r.policy_rule == "extraction-failed" and r.degraded


async def test_budget_zero_keeps_rules_and_clean_fast_path(policy):
    policy.budgets.daily_tokens_tier2 = 0
    e = engine(policy)
    r = await e.inspect(FLAGGED, "web", policy.agent)
    assert r.policy_rule == "budget-hold" and r.degraded and r.budget_degraded
    assert e.decision_model.calls == 0
    clean = await e.inspect("Quarterly report.", "web", policy.agent)
    assert clean.decision == Decision.ALLOW and not clean.budget_degraded


async def test_usage_persisted_cache_free_and_budget_per_agent(policy):
    policy.budgets.daily_tokens_tier2 = 10
    judge = StaticDecisionModel()
    judge.result.input_tokens, judge.result.est_cost, judge.result.model = 10, 0.001, "test-model"
    e = engine(policy, decision_model=judge)
    first = await e.inspect(FLAGGED, "web", policy.agent)
    repeat = await e.inspect(FLAGGED, "web", policy.agent)
    assert not first.budget_degraded and not repeat.budget_degraded and judge.calls == 1
    rows = e.store.query("SELECT input_tokens, est_cost, model FROM decisions ORDER BY id")
    assert rows == [{"input_tokens": 10, "est_cost": 0.001, "model": "test-model"},
                    {"input_tokens": 0, "est_cost": 0.0, "model": "test-model"}]
    restarted = engine(policy, store=e.store)
    assert (await restarted.inspect(FLAGGED + " new", "web", policy.agent)).budget_degraded
    other = policy.model_copy(deep=True)
    other.agent = "other-agent"
    assert not (await engine(other, store=e.store).inspect(FLAGGED, "web", other.agent)).budget_degraded


async def test_budget_day_rollover(policy):
    policy.budgets.daily_tokens_tier2 = 10
    now = [time.time()]
    judge = StaticDecisionModel()
    judge.result.input_tokens = 10
    e = engine(policy, decision_model=judge, clock=lambda: now[0], cache_size=0)
    await e.inspect(FLAGGED, "web", policy.agent)
    assert (await e.inspect(FLAGGED, "web", policy.agent)).budget_degraded
    now[0] += 86400
    assert not (await e.inspect(FLAGGED, "web", policy.agent)).budget_degraded


async def test_concurrent_inspections_cannot_both_enter_at_budget_cap(policy):
    policy.budgets.daily_tokens_tier2 = 10
    judge = StaticDecisionModel()
    judge.result.input_tokens = 10
    e = engine(policy, decision_model=judge)
    a, b = await asyncio.gather(e.inspect(FLAGGED, "web", policy.agent),
                               e.inspect(FLAGGED + " More facts.", "web", policy.agent))
    assert not a.budget_degraded and b.budget_degraded and judge.calls == 1


async def test_cache_is_context_scoped_and_bounded(policy):
    e = engine(policy, cache_size=2)
    await e.inspect(FLAGGED, "web", policy.agent, task="Task one")
    await e.inspect(FLAGGED, "web", policy.agent, task="Task two")
    await e.inspect(FLAGGED, "api", policy.agent, task="Task two")
    assert e.decision_model.calls == 3 and len(e._cache) <= 2


async def test_cache_expiry_retries_and_failures_not_cached(policy):
    now = [time.time()]
    e = engine(policy, clock=lambda: now[0], cache_ttl_s=1)
    await e.inspect(FLAGGED, "web", policy.agent)
    now[0] += 2
    await e.inspect(FLAGGED, "web", policy.agent)
    assert e.decision_model.calls == 2
    e.decision_model.result.degraded = True
    now[0] += 2
    await e.inspect(FLAGGED, "web", policy.agent)
    await e.inspect(FLAGGED, "web", policy.agent)
    assert e.decision_model.calls == 4


async def test_session_task_trusted_values_and_provenance_reach_action_guard(policy):
    e = engine(policy)
    s = e.start_session(policy.agent, user_ref="person-reference", task="Summarise the report",
                        trusted={"customer_id": "C-1042"})
    assert s.user_ref != "person-reference" and len(s.user_ref) == 16
    await e.inspect("finance@example-corp.test prepared the report.", "web", policy.agent, s.session_id)
    r = await e.check_action("send_message", {"to": "finance@example-corp.test", "body": "Report ready"},
                             policy.agent, s.session_id)
    assert r.decision == Decision.ESCALATE and r.policy_rule == "target-from-untrusted-content"
    query = await e.check_action("query_db", {"customer_id": "C-2001"}, policy.agent, s.session_id)
    assert query.final_args["customer_id"] == "C-1042" and query.event_id
    events = e.logger.session_events(s.session_id)
    assert [row["seq"] for row in events] == [1, 2, 3]
    assert events[-1]["action"]["tool"] == "query_db"
    await e.inspect("Ordinary notes", "user", policy.agent, s.session_id, task="Email finance@example-corp.test")
    assert s.task == "Email finance@example-corp.test" and not s.from_untrusted_only("finance@example-corp.test")


async def test_outbound_secrets_redacted_everywhere_and_session_risk_persisted(policy):
    secret, canary = "private-report-reference", "protected-canary-value"
    policy.sensitive_data.canaries = [canary]
    judge = StaticDecisionModel(0.7)
    judge.result.model = "test/" + secret
    e = engine(policy, decision_model=judge)
    e.register_secrets(iter([secret]))
    s = e.start_session(policy.agent, task="Summarise " + secret)
    await e.inspect('<span hidden>' + secret + " " + canary + '</span>', "web:" + secret, policy.agent, s.session_id)
    args = {"path": "notes/report.txt", "text": secret + " " + canary}
    r = await e.check_action("write_file", args, policy.agent, s.session_id)
    assert r.policy_rule == "outbound-secret" and r.final_args is None and r.event_id
    for table in ("sessions", "events", "findings", "decisions", "actions"):
        stored = json.dumps(e.store.query("SELECT * FROM " + table))
        assert secret not in stored and canary not in stored
    assert e.store.query("SELECT risk FROM sessions")[0]["risk"] == s.risk


async def test_preview_disabled_still_redacts_metadata(policy, monkeypatch):
    monkeypatch.setenv("ASG_STORE_PREVIEWS", "0")
    e = engine(policy)
    secret = "private-reference"
    e.register_secrets([secret])
    await e.inspect("Report " + secret, "web:" + secret, policy.agent)
    row = e.logger.decisions()[0]
    assert row["preview"] == "" and secret not in row["source"]


async def test_cross_agent_session_rejected_before_state_change(policy):
    e = engine(policy)
    s = e.start_session(policy.agent)
    with pytest.raises(ValueError, match="different agent"):
        await e.inspect("Report ready", "web", "other-agent", s.session_id)
    with pytest.raises(ValueError, match="different agent"):
        await e.check_action("query_db", {}, "other-agent", s.session_id)
    assert s.turns == 0 and e.logger.session_events(s.session_id) == []


def test_sync_wrappers(policy):
    e = engine(policy)
    s = e.start_session(policy.agent)
    assert e.inspect_sync("Report ready", "web", policy.agent, s.session_id).decision == Decision.ALLOW
    assert e.check_action_sync("read_email", {}, policy.agent, s.session_id).decision == Decision.ALLOW


async def test_sync_wrappers_reject_running_loop(policy):
    e = engine(policy)
    with pytest.raises(RuntimeError, match="await"):
        e.inspect_sync("Report ready", "web", policy.agent)
    with pytest.raises(RuntimeError, match="await"):
        e.check_action_sync("read_email", {}, policy.agent)


def test_constructor_rejects_invalid_limits(policy):
    with pytest.raises(ValueError):
        engine(policy, segment_chars=0)
    with pytest.raises(ValueError):
        engine(policy, cache_size=-1)


async def test_unflagged_plain_text_is_classified_and_escalated(policy):
    """D-019: content with no structural signal still reaches Tier 1; a high score escalates to the judge."""
    e = engine(policy, malicious=0.9, classifiers=[Scorer(0.99)])
    r = await e.inspect("Ordinary words. " + MARKER + " more words.", "web", policy.agent, fmt="text")
    assert e.classifiers[0].calls and e.decision_model.calls == 1
    assert r.decision in (Decision.NEUTRALISE, Decision.BLOCK)


async def test_unflagged_low_score_skips_judge(policy):
    e = engine(policy, malicious=0.9, classifiers=[Scorer(0.1)])
    r = await e.inspect("Ordinary words. " + MARKER, "web", policy.agent, fmt="text")
    assert r.decision == Decision.ALLOW and e.decision_model.calls == 0


async def test_judge_untrusted_always_assesses_low_scoring_documents(policy):
    # DEF-017: Tier 1 scores paraphrased injections near 0, so high-risk agents send every untrusted document
    # to the judge; user turns and very short tool output keep the classifier gate (fast path).
    policy.thresholds.judge_untrusted = "always"
    e = engine(policy, malicious=0.95, classifiers=[Scorer(0.0)])
    doc = "Supplier update: the attached price list replaces the one from September for all regions."
    r = await e.inspect(doc, "web", policy.agent)
    assert r.tier == 2 and r.decision == Decision.BLOCK and e.decision_model.calls == 1
    assert (await e.inspect("sent (sandbox outbox)", "tool:send_message", policy.agent)).tier == 1
    assert (await e.inspect(doc, "user", policy.agent)).tier == 1 and e.decision_model.calls == 1
    policy.thresholds.judge_untrusted = "classifier"
    assert (await engine(policy, malicious=0.95, classifiers=[Scorer(0.0)]).inspect(doc, "web", policy.agent)).tier == 1


async def test_homoglyph_text_reaches_judge_ascii_folded(policy):
    seen = []

    class Judge(StaticDecisionModel):
        async def assess(self, content, source, task=""):
            seen.append(content)
            return await super().assess(content, source, task)

    e = engine(policy, decision_model=Judge(0.0))
    await e.inspect("Please rеviеw the quаrterly rеport bеfore the meeting", "web", policy.agent)   # Cyrillic е/а
    assert seen and "[ascii view] Please review the quarterly report before the meeting" in seen[0]


def test_budget_override_from_environment(monkeypatch):
    monkeypatch.setenv("ASG_BUDGET_TIER2_DAILY_TOKENS", "none")
    assert load_policy("research-agent").budgets.daily_tokens_tier2 is None
    monkeypatch.setenv("ASG_BUDGET_TIER2_DAILY_TOKENS", "5000")
    assert load_policy("research-agent").budgets.daily_tokens_tier2 == 5000
    monkeypatch.delenv("ASG_BUDGET_TIER2_DAILY_TOKENS")
    assert load_policy("research-agent").budgets.daily_tokens_tier2 == 200000
