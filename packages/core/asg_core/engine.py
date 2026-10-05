"""Shared inspection and action boundary (CORE-1, 4–8, 10, 12, 14, 15).

Structural rules select short classifier inputs; classifiers only advise escalation.
Cached scans/assessments never cache enforcement or session risk.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect as inspectlib
import json
import math
import re
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from . import action_guard
from .classifier import local_classifier
from .decision_model import Assessment, DecisionModel, make_decision_model
from .extract import ExtractedDoc, extract
from .llm.router import Router
from .logger import DecisionLogger
from .normalise import normalise
from .policy import AgentPolicy, load_policy
from .secrets import registry
from .session import Session, SessionStore
from .store import Store
from .types import ATTACK_TYPES, ActionResult, Decision, Finding, InspectResult


@dataclass
class _Scan:
    doc: ExtractedDoc
    view: str
    findings: list[Finding]
    chunks: list[tuple[int, int, str, str]]
    all_chunks: list[tuple[int, int, str, str]] | None = None   # every chunk, for Tier 1 on unflagged content


def _probability(value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("invalid probability")
    return value


def _sync(call: Callable[[], Any]) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(call())
    raise RuntimeError("An event loop is running; await the async Engine method instead")


class Engine:
    def __init__(self, *, policy_loader: Callable[[str], AgentPolicy] = load_policy,
                 decision_model: DecisionModel | None = None, classifiers: Iterable[Any] | None = None,
                 router: Router | None = None, store: Store | None = None,
                 logger: DecisionLogger | None = None, sessions: SessionStore | None = None,
                 policy_directory: Path | None = None, tier0_timeout_s: float = 2.0,
                 tier1_timeout_s: float = 1.0, tier2_timeout_s: float = 15.0,
                 segment_chars: int = 1000, encoded_min_chars: int = 48,
                 cache_size: int = 256, cache_ttl_s: float = 3600,
                 clock: Callable[[], float] = time.time) -> None:
        if min(tier0_timeout_s, tier1_timeout_s, tier2_timeout_s, segment_chars, encoded_min_chars) <= 0:
            raise ValueError("time budgets and scan sizes must be positive")
        if cache_size < 0 or cache_ttl_s < 0:
            raise ValueError("cache limits must be non-negative")
        if logger is not None and store is not None and logger.store is not store:
            raise ValueError("logger and engine must share a store")
        self.router = router
        self.store = logger.store if logger else (store or (router.store if router else Store(":memory:")))
        self.logger = logger or DecisionLogger(self.store)
        self.sessions = sessions or SessionStore()
        self.policy_loader = (lambda agent: load_policy(agent, policy_directory)) if policy_directory else policy_loader
        self.decision_model = decision_model
        self.classifiers = None if classifiers is None else list(classifiers)
        self.tier0_timeout_s, self.tier1_timeout_s, self.tier2_timeout_s = (
            tier0_timeout_s, tier1_timeout_s, tier2_timeout_s)
        self.segment_chars = segment_chars
        self._encoded = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{" + str(encoded_min_chars) + r",}={0,2}")
        self.cache_size, self.cache_ttl_s, self.clock = cache_size, cache_ttl_s, clock
        self._cache: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._models: dict[str, DecisionModel] = {}
        self._secrets: list[str] = []
        self._agent_locks: dict[str, asyncio.Lock] = {}

    def _policy(self, agent_id: str) -> AgentPolicy:
        policy = self.policy_loader(agent_id)
        self.register_secrets(policy.canary_values())
        return policy

    def register_secrets(self, values: Iterable[str]) -> None:
        for value in values:
            if value and value not in self._secrets:
                self._secrets.append(value)
                registry.register(value)
                self.logger.add_secrets([value])

    def start_session(self, agent_id: str, user_ref: str | None = None, task: str = "",
                      trusted: dict[str, Any] | None = None) -> Session:
        self._policy(agent_id)
        session = self.sessions.create(agent_id, user_ref=user_ref, task=task, trusted=dict(trusted or {}))
        self.logger.session(session.session_id, agent_id, session.user_ref, task)
        return session

    def _session(self, agent_id: str, session_id: str | None) -> Session:
        session = self.sessions.get(session_id, agent_id)
        if session.agent_id != agent_id:
            raise ValueError("session belongs to a different agent")
        self.logger.session(session.session_id, agent_id, session.user_ref, session.task)
        return session

    def _get(self, key: str) -> Any:
        hit = self._cache.get(key)
        if hit is None:
            return None
        if self.clock() >= hit[0]:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return hit[1]

    def _put(self, key: str, value: Any) -> None:
        if not self.cache_size or not self.cache_ttl_s:
            return
        self._cache[key] = (self.clock() + self.cache_ttl_s, value)
        self._cache.move_to_end(key)
        while len(self._cache) > self.cache_size:
            self._cache.popitem(last=False)

    @staticmethod
    def _key(*parts: Any) -> str:
        return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()

    def _scan(self, content: str | bytes, source: str, filename: str | None, fmt: str | None) -> _Scan:
        doc = extract(content, fmt=fmt, filename=filename, source=source)
        findings, chunks, views, all_chunks = [], [], [], []
        for segment in doc.segments:
            views.append(normalise(segment.text).text)
            encoded = list(self._encoded.finditer(segment.text))
            for offset in range(0, len(segment.text), self.segment_chars):
                text = segment.text[offset:offset + self.segment_chars]
                norm = normalise(text)
                span = (segment.start + offset, segment.start + offset + len(text))
                signals = sorted(norm.flags)
                if not segment.visible:
                    signals.append("non-visible-content")
                if any(m.start() < offset + len(text) and m.end() > offset for m in encoded):
                    signals.append("encoded-blob")
                for signal in signals:
                    labels = ["Indirect Prompt Injection"] if signal == "non-visible-content" else ["Encoded Instructions"]
                    findings.append(Finding(span=span, preview=text, origin=segment.origin,
                                            signal=signal, labels=labels))
                if norm.changes:
                    findings.append(Finding(span=span, preview=text, origin=segment.origin,
                                            signal="normalisation:" + json.dumps(norm.changes, sort_keys=True),
                                            labels=["Encoded Instructions"]))
                for _, view in norm.views():
                    for start in range(0, len(view), self.segment_chars):
                        chunk = (*span, segment.origin, view[start:start + self.segment_chars])
                        all_chunks.append(chunk)
                        if signals:
                            chunks.append(chunk)
        return _Scan(doc, "\n".join(views), findings, chunks, all_chunks)

    async def _scores(self, chunks: list[tuple[int, int, str, str]]) -> list[Finding]:
        scorers = self.classifiers
        if scorers is None:
            scorer = await asyncio.to_thread(local_classifier)
            if scorer is None:
                raise RuntimeError("local classifier unavailable")
            scorers = [scorer]
        findings = []
        for start, end, origin, text in chunks:
            for scorer in scorers:
                if inspectlib.iscoroutinefunction(scorer.score):
                    value = await scorer.score(text)
                else:
                    value = await asyncio.to_thread(scorer.score, text)
                    if inspectlib.isawaitable(value):
                        value = await value
                if value is None:
                    raise RuntimeError("classifier unavailable")
                findings.append(Finding(span=(start, end), origin=origin, signal="classifier",
                                        labels=["Indirect Prompt Injection"], score=_probability(value), tier=1))
        return findings

    def _tokens_today(self, agent_id: str) -> int:
        now = self.clock()
        start = now - now % 86400
        rows = self.store.query("SELECT COALESCE(SUM(input_tokens), 0) AS tokens FROM decisions "
                                "WHERE agent_id = ? AND created_at >= ?", (agent_id, start))
        return int(rows[0]["tokens"])

    async def _judge(self, scan: _Scan, source: str, task: str, policy: AgentPolicy,
                     agent_id: str) -> tuple[Assessment, bool]:
        # Agent/policy/task/source isolate assessments; state and enforcement are recomputed.
        key = self._key("judge", scan.view, source, task, agent_id, policy.model_dump())
        cached = self._get(key)
        if cached is not None:
            return Assessment(**{**cached.__dict__, "input_tokens": 0, "est_cost": 0.0}), False
        cap = policy.budgets.daily_tokens_tier2
        if cap is not None and self._tokens_today(agent_id) >= cap:
            return Assessment(0, degraded=True), True
        try:
            model = self.decision_model
            if model is None:
                model = self._models.get(policy.decision_model)
                if model is None:
                    if policy.decision_model == "generative_free" and self.router is None:
                        self.router = Router(store=self.store)
                    model = make_decision_model(policy.decision_model, self.router)
                    self._models[policy.decision_model] = model
            assessment = await asyncio.wait_for(model.assess(scan.view, source, task), self.tier2_timeout_s)
            _probability(assessment.malicious)
            for value in assessment.categories.values():
                _probability(value)
            if assessment.input_tokens < 0 or not math.isfinite(assessment.est_cost) or assessment.est_cost < 0:
                raise ValueError("invalid judge usage")
        except Exception:
            return Assessment(0, degraded=True), False
        if not assessment.degraded:
            self._put(key, deepcopy(assessment))
        return assessment, False

    @staticmethod
    def _judge_findings(scan: _Scan, assessment: Assessment, labels: list[str]) -> list[Finding]:
        spans: set[tuple[int, int]] = set()
        for quote in assessment.evidence:
            if not quote:
                continue
            start = 0
            while (pos := scan.doc.text.find(quote, start)) >= 0:
                spans.add((pos, pos + len(quote)))
                start = pos + len(quote)
        # Normalisation can change lengths; never treat detection-view offsets as original offsets.
        if not spans:
            spans = {(start, end) for start, end, _, _ in scan.chunks}
        return [Finding(span=span, preview=scan.doc.text[span[0]:span[1]],
                        origin=next((s.origin for s in scan.doc.segments if s.start <= span[0] < s.end), ""),
                        signal="judge", labels=labels, score=assessment.malicious, tier=2)
                for span in sorted(spans)]

    @staticmethod
    def _quarantine(text: str, spans: list[tuple[int, int]]) -> str:
        merged: list[tuple[int, int]] = []
        for start, end in sorted(set(spans)):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((start, end))
        for start, end in reversed(merged):
            text = text[:start] + "[QUARANTINED]" + text[end:]
        # A fresh boundary cannot be closed by a marker already present in the data.
        import secrets

        boundary = "UNTRUSTED-" + secrets.token_hex(8)
        return f"<<{boundary}>>\n{text}\n<</{boundary}>>"

    async def inspect(self, content: str | bytes, source: str, agent_id: str, session_id: str | None = None,
                      filename: str | None = None, fmt: str | None = None, task: str | None = None) -> InspectResult:
        # Serialise agent decisions through accounting/logging, including concurrent sessions.
        async with self._agent_locks.setdefault(agent_id, asyncio.Lock()):
            return await self._inspect(content, source, agent_id, session_id, filename, fmt, task)

    async def _inspect(self, content, source, agent_id, session_id, filename, fmt, task) -> InspectResult:
        t0 = time.perf_counter()
        policy = self._policy(agent_id)
        session = self._session(agent_id, session_id)
        session.new_turn(policy.session.risk_decay_per_turn)
        if task is not None:
            session.task = task
            session.note_trusted(task)
        assessment, tier, degraded, budget_degraded = Assessment(0), 0, False, False
        key = self._key("scan", hashlib.sha256(content if isinstance(content, bytes) else content.encode()).hexdigest(),
                        source, filename, fmt)
        scan = self._get(key)
        if scan is None:
            try:
                scan = await asyncio.wait_for(asyncio.to_thread(self._scan, content, source, filename, fmt),
                                              self.tier0_timeout_s)
                if not scan.doc.warnings:
                    self._put(key, scan)
            except Exception:
                raw = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
                scan = _Scan(ExtractedDoc(fmt or "text", text=raw), "", [], [])
                scan.doc.warnings.append("inspection unavailable")
        findings = [f.model_copy(deep=True) for f in scan.findings]
        if scan.doc.warnings:
            degraded = True
            findings.append(Finding(signal="extraction-unavailable", labels=["Indirect Prompt Injection"]))
        if source == "user":
            session.note_trusted(scan.doc.text)
        else:
            session.note_untrusted(scan.doc.text)
            session.flagged_untrusted |= bool(scan.chunks or scan.doc.warnings)
        if scan.chunks:
            tier = 1
            score_key = self._key("scores", key)
            scored = self._get(score_key)
            if scored is None:
                try:
                    scored = await asyncio.wait_for(self._scores(scan.chunks), self.tier1_timeout_s)
                    self._put(score_key, scored)
                except Exception:
                    degraded = True
                    scored = []
            findings.extend(f.model_copy(deep=True) for f in scored)
            # Structural suspicion always needs resolution; low classifier scores cannot clear it.
            tier = 2
            assessment, budget_degraded = await self._judge(scan, source, session.task or policy.task_scope, policy, agent_id)
            degraded |= assessment.degraded
        elif scan.all_chunks and source != "system":
            # No structural signal: Tier 1 scores every chunk; only chunks at or above the policy's
            # escalation threshold go to the Tier 2 judge (D-011: the classifier never decides alone).
            tier = 1
            score_key = self._key("scores-all", key)
            scored = self._get(score_key)
            if scored is None:
                try:
                    scored = await asyncio.wait_for(self._scores(scan.all_chunks), self.tier1_timeout_s * 4)
                    self._put(score_key, scored)
                except Exception:
                    degraded = True
                    scored = []
            low = policy.thresholds.escalate_band[0]
            hot_spans = {(f.span, f.origin) for f in scored if f.score >= low}
            if hot_spans:
                findings.extend(f.model_copy(deep=True) for f in scored if f.score >= low)
                scan.chunks = [c for c in scan.all_chunks if ((c[0], c[1]), c[2]) in hot_spans]
                if source != "user":
                    session.flagged_untrusted = True
                tier = 2
                assessment, budget_degraded = await self._judge(scan, source, session.task or policy.task_scope, policy, agent_id)
                degraded |= assessment.degraded
        judge_labels = sorted(k for k, score in assessment.categories.items() if k in ATTACK_TYPES and score > 0)
        judge_labels = judge_labels or (["Instruction Override"] if source == "user" else ["Indirect Prompt Injection"])
        if assessment.malicious > 0 and not assessment.degraded:
            findings.extend(self._judge_findings(scan, assessment, judge_labels))
        hidden = [(f.span[0], f.span[1]) for f in findings
                  if f.signal == "non-visible-content" and f.span and policy.sensitive_data.drop_non_visible]
        risk = max(assessment.malicious if not assessment.degraded else 0.0,
                   policy.thresholds.neutralise if hidden else 0.0)
        labels = sorted({label for f in findings for label in f.labels})
        session.add_risk(risk, labels)
        if scan.doc.warnings:
            decision, rule, reason = Decision.BLOCK, "extraction-failed", "Content could not be fully inspected"
        elif risk >= policy.thresholds.block:
            decision, rule, reason = Decision.BLOCK, "content-risk-block", "Content risk reached the policy block threshold"
        elif session.risk >= policy.session.block_at:
            decision, rule, reason = Decision.BLOCK, "session-risk-block", "Accumulated session risk reached the block threshold"
        elif assessment.degraded and scan.chunks:
            decision, rule, reason = (Decision.BLOCK, "budget-hold" if budget_degraded else "judge-unavailable-hold",
                                      "Flagged content is held until it can be assessed")
        elif session.risk >= policy.session.escalate_at:
            decision, rule, reason = Decision.ESCALATE, "session-risk-escalate", "Accumulated session risk requires review"
        elif hidden:
            decision, rule, reason = Decision.NEUTRALISE, "drop-non-visible", "Non-visible content quarantined by policy"
        elif risk >= policy.thresholds.neutralise:
            decision, rule, reason = Decision.NEUTRALISE, "judge-neutralise", "Assessed spans reached the policy neutralise threshold"
        else:
            decision, rule, reason = Decision.ALLOW, "allow", "Content is within policy"
        enforced = decision if policy.mode == "enforce" else Decision.ALLOW
        original = content if isinstance(content, str) and scan.doc.format == "text" else scan.doc.text
        cleaned = original
        if enforced in (Decision.BLOCK, Decision.ESCALATE):
            cleaned = "[Content held by the security policy: " + rule + "]"
        elif enforced == Decision.NEUTRALISE:
            spans = hidden + [f.span for f in findings if f.signal == "judge" and f.span
                              and f.score >= policy.thresholds.neutralise]
            offset = original.find(scan.doc.text) if scan.doc.format == "text" else 0
            cleaned = self._quarantine(original, [(start + offset, end + offset) for start, end in spans])
        for finding in findings:
            if finding.span:
                finding.preview = self.logger.scrub(scan.doc.text[finding.span[0]:finding.span[1]])
        result = InspectResult(decision=decision, enforced=enforced, cleaned_content=cleaned, findings=findings,
                               labels=labels, risk=risk, session_risk=session.risk, policy_rule=rule, reason=reason,
                               tier=tier, degraded=degraded, budget_degraded=budget_degraded,
                               latency_ms=round((time.perf_counter() - t0) * 1000, 2))
        result.event_id = self.logger.inspection(session.session_id, agent_id, source, scan.doc.text, result,
                                                  assessment.model, assessment.input_tokens, assessment.est_cost)
        return result

    async def check_action(self, tool: str, args: dict[str, Any], agent_id: str,
                           session_id: str | None = None) -> ActionResult:
        async with self._agent_locks.setdefault(agent_id, asyncio.Lock()):
            policy, session = self._policy(agent_id), self._session(agent_id, session_id)
            result = action_guard.check_action(tool, args, policy, session, self._secrets)
            result.event_id = self.logger.action(session.session_id, agent_id, tool, args, result, session.risk)
            self.store.execute("UPDATE sessions SET risk = ? WHERE id = ?", (session.risk, session.session_id))
            return result

    def inspect_sync(self, *args: Any, **kwargs: Any) -> InspectResult:
        return _sync(lambda: self.inspect(*args, **kwargs))

    def check_action_sync(self, *args: Any, **kwargs: Any) -> ActionResult:
        return _sync(lambda: self.check_action(*args, **kwargs))
