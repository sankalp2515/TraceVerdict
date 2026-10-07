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
import os
import re
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Iterable

from . import action_guard
from .classifier import local_classifier
from .decision_model import Assessment, DecisionModel, make_decision_model
from . import markers
from .decode import decode_views
from .extract import ExtractedDoc, extract
from .llm.router import Router
from .logger import DecisionLogger
from .memory import AttackMemory, Match
from .normalise import normalise
from .policy import AgentPolicy, load_policy, policy_exists
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
                 memory: AttackMemory | None = None,
                 policy_directory: Path | None = None, tier0_timeout_s: float = 2.0,
                 tier1_timeout_s: float = 1.0, tier2_timeout_s: float = 15.0,
                 segment_chars: int = 1000, encoded_min_chars: int = 48,
                 judge_window_chars: int = 6000, judge_max_windows: int | None = None, max_text_chars: int | None = None,
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
        self.memory = memory or AttackMemory(self.store)
        # Recent extracted text by event id (in process only, never persisted) so a reviewer can confirm an
        # attack or mark a false positive on a fresh decision; the memory itself keeps fingerprints only.
        self._recent: OrderedDict[str, tuple[str, str]] = OrderedDict()
        self.recent_size = 500
        self.sessions = sessions or SessionStore()
        self.policy_loader = (lambda agent: load_policy(agent, policy_directory)) if policy_directory else policy_loader
        self._policy_files = (policy_directory, policy_directory is not None or policy_loader is load_policy)
        self.logger.org_of = self._org_of
        self.decision_model = decision_model
        self.classifiers = None if classifiers is None else list(classifiers)
        self.tier0_timeout_s, self.tier1_timeout_s, self.tier2_timeout_s = (
            tier0_timeout_s, tier1_timeout_s, tier2_timeout_s)
        self.segment_chars = segment_chars
        self.judge_window_chars = judge_window_chars
        self.judge_max_windows = judge_max_windows or int(os.environ.get("INTENTSEAL_JUDGE_MAX_WINDOWS") or 8)
        self.tier1_per_chunk_s = float(os.environ.get("INTENTSEAL_TIER1_PER_CHUNK_S") or 0.75)
        self.tier1_max_s = float(os.environ.get("INTENTSEAL_TIER1_MAX_S") or 30)
        self.max_text_chars = max_text_chars or int(os.environ.get("INTENTSEAL_MAX_TEXT_CHARS") or 1_000_000)
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

    def _org_of(self, agent_id: str) -> str | None:
        try:
            return self.policy_loader(agent_id).org
        except Exception:
            return None

    def has_policy(self, agent_id: str) -> bool:
        """Is this agent configured? Policies come from files unless a custom loader was given."""
        directory, from_files = self._policy_files
        return policy_exists(agent_id, directory) if from_files else True

    def register_secrets(self, values: Iterable[str]) -> None:
        for value in values:
            if value and value not in self._secrets:
                self._secrets.append(value)
                registry.register(value)
                self.logger.add_secrets([value])

    def start_session(self, agent_id: str, user_ref: str | None = None, task: str = "",
                      trusted: dict[str, Any] | None = None, session_id: str | None = None) -> Session:
        self._policy(agent_id)
        session = self.sessions.create(agent_id, user_ref=user_ref, task=task, trusted=dict(trusted or {}),
                                       session_id=session_id)
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
            seg_norm = normalise(segment.text)
            views.append(seg_norm.text)
            if seg_norm.flags & {"mixed_script", "confusable_characters"}:
                views.append("[ascii view] " + (seg_norm.skeleton or seg_norm.ascii_view))   # look-alikes folded by shape
            encoded = list(self._encoded.finditer(segment.text))
            forged = markers.find(segment.text)   # forged role / tool-call markers (docs/13 L4)
            for m in forged:
                findings.append(Finding(span=(segment.start + m.start(), segment.start + m.end()), preview=m.group(0),
                                        origin=segment.origin, signal="role-marker", labels=["Role Change"]))
            for offset in range(0, len(segment.text), self.segment_chars):
                text = segment.text[offset:offset + self.segment_chars]
                norm = normalise(text)
                span = (segment.start + offset, segment.start + offset + len(text))
                signals = sorted(norm.flags)
                if not segment.visible:
                    signals.append("non-visible-content")
                if any(m.start() < offset + len(text) and m.end() > offset for m in encoded):
                    signals.append("encoded-blob")
                if any(m.start() < offset + len(text) and m.end() > offset for m in forged):
                    signals.append("role-markers")
                for signal in signals:
                    labels = {"non-visible-content": ["Indirect Prompt Injection"],
                              "role-markers": ["Role Change"]}.get(signal, ["Encoded Instructions"])
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
            # CORE-3: decode before scoring. Decoded text is an extra view (always escalated); spans point at the
            # encoded run in the original, so a neutralise quarantines the encoded text itself.
            for d in decode_views(segment.text):
                span = (segment.start + d.span[0], segment.start + d.span[1])
                findings.append(Finding(span=span, preview=d.text, origin=segment.origin, signal="decoded:" + d.kind,
                                        labels=["Encoded Instructions"]))
                views.append(f"[decoded {d.kind}] {normalise(d.text).text}")
                for start in range(0, len(d.text), self.segment_chars):
                    chunk = (*span, segment.origin, normalise(d.text[start:start + self.segment_chars]).ascii_view)
                    chunks.append(chunk)
                    all_chunks.append(chunk)
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

    def _judge_windows(self, scan: _Scan, priority: dict[tuple[int, int], float] | None = None
                       ) -> tuple[list[tuple[str, list[tuple[int, int]]]], list[tuple[int, int]]]:
        """CORE-16: what the judge reads. A document whose detection view fits one window is judged whole (with its
        context). A longer one is judged as windows of its flagged chunks, in document order, each window carrying
        the original spans it covers; at most `judge_max_windows` windows, the most suspicious first. Returns the
        windows and the spans that did not fit (never silently dropped: the caller decides on them)."""
        flagged = sorted({(c[0], c[1]) for c in scan.chunks})
        if len(scan.view) <= self.judge_window_chars:
            return [(scan.view, [])], []   # judged whole: no span list means "the whole document"
        views: dict[tuple[int, int], list[str]] = {}
        for start, end, _, text in scan.chunks:
            views.setdefault((start, end), []).append(text)
        windows: list[tuple[str, list[tuple[int, int]]]] = []
        text, spans = "", []
        for span in flagged:
            piece = "\n".join(dict.fromkeys(views[span]))[: self.judge_window_chars]
            if text and len(text) + len(piece) + 1 > self.judge_window_chars:
                windows.append((text, spans))
                text, spans = "", []
            text, spans = (text + "\n" + piece if text else piece), spans + [span]
        if text:
            windows.append((text, spans))
        if len(windows) <= self.judge_max_windows:
            return windows, []
        rank = lambda w: max((priority or {}).get(s, 1.0) for s in w[1])   # unscored (structural) chunks first
        ordered = sorted(range(len(windows)), key=lambda i: (-rank(windows[i]), i))
        keep = sorted(ordered[: self.judge_max_windows])
        dropped = [s for i in ordered[self.judge_max_windows:] for s in windows[i][1]]
        return [windows[i] for i in keep], dropped

    async def _judge(self, scan: _Scan, source: str, task: str, policy: AgentPolicy, agent_id: str,
                     priority: dict[tuple[int, int], float] | None = None
                     ) -> tuple[Assessment, bool, list[tuple[int, int]]]:
        """Tier 2 over the judge windows. Returns the combined assessment (highest risk wins; usage summed; degraded
        if any window could not be assessed), whether the daily budget stopped it, and the spans left unjudged."""
        windows, unjudged = self._judge_windows(scan, priority)
        cap = policy.budgets.daily_tokens_tier2
        results: list[Assessment | None] = []
        pending: list[tuple[int, str, str]] = []
        for i, (text, _) in enumerate(windows):
            # Agent/policy/task/source isolate assessments; state and enforcement are recomputed.
            key = self._key("judge", text, source, task, agent_id, policy.model_dump())
            cached = self._get(key)
            results.append(None if cached is None else
                           Assessment(**{**cached.__dict__, "input_tokens": 0, "output_tokens": 0, "est_cost": 0.0}))
            if cached is None:
                pending.append((i, key, text))
        if pending and cap is not None and self._tokens_today(agent_id) >= cap:
            return Assessment(0, degraded=True), True, unjudged
        if pending:
            model = self._decision_model(policy)
            sem = asyncio.Semaphore(3)

            async def one(i: int, key: str, text: str) -> None:
                async with sem:
                    results[i] = await self._assess(model, key, text, source, task)

            await asyncio.gather(*(one(*p) for p in pending))
        combined = Assessment(0.0)
        for (_, spans), a in zip(windows, results):
            assert a is not None
            combined.degraded |= a.degraded
            combined.input_tokens += a.input_tokens
            combined.output_tokens += a.output_tokens
            combined.est_cost += a.est_cost
            combined.model = combined.model or a.model
            if a.degraded:
                continue
            for k, v in a.categories.items():
                combined.categories[k] = max(v, combined.categories.get(k, 0.0))
            if a.malicious > 0:
                combined.evidence += [q for q in a.evidence if q not in combined.evidence]
                combined.spans += [s for s in spans if s not in combined.spans]
            combined.malicious = max(combined.malicious, a.malicious)
        return combined, False, unjudged

    def _decision_model(self, policy: AgentPolicy) -> DecisionModel:
        model = self.decision_model
        if model is None:
            model = self._models.get(policy.decision_model)
            if model is None:
                if policy.decision_model == "generative_free" and self.router is None:
                    self.router = Router(store=self.store)
                model = make_decision_model(policy.decision_model, self.router)
                self._models[policy.decision_model] = model
        return model

    async def _assess(self, model: DecisionModel, key: str, text: str, source: str, task: str) -> Assessment:
        try:
            assessment = await asyncio.wait_for(model.assess(text, source, task), self.tier2_timeout_s)
            _probability(assessment.malicious)
            for value in assessment.categories.values():
                _probability(value)
            if assessment.input_tokens < 0 or not math.isfinite(assessment.est_cost) or assessment.est_cost < 0:
                raise ValueError("invalid judge usage")
        except Exception:
            return Assessment(0, degraded=True)
        if not assessment.degraded:
            self._put(key, deepcopy(assessment))
        return assessment

    @staticmethod
    def _judge_findings(scan: _Scan, assessment: Assessment, labels: list[str]) -> list[Finding]:
        # Evidence quotes are located in the original text: anywhere when the document was judged whole, otherwise
        # inside the windows the judge called malicious. Never detection-view offsets.
        text = scan.doc.text
        regions = sorted(assessment.spans) or [(0, len(text))]
        spans: set[tuple[int, int]] = set()
        for quote in assessment.evidence:
            if not quote:
                continue
            for lo, hi in regions:
                start = lo
                while (pos := text.find(quote, start, min(len(text), hi + len(quote)))) >= 0:
                    spans.add((pos, pos + len(quote)))
                    start = pos + len(quote)
        if not spans:   # quote not found verbatim (normalised/decoded view): the windows' own chunk spans
            spans = set(assessment.spans) or {(start, end) for start, end, _, _ in scan.chunks}
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

    def _remember_recent(self, event_id: str | None, agent_id: str, text: str) -> None:
        if event_id and self.recent_size:
            self._recent[event_id] = (agent_id, text)
            while len(self._recent) > self.recent_size:
                self._recent.popitem(last=False)

    def feedback(self, verdict: str, *, event_id: str | None = None, content: str | bytes | None = None,
                 agent_id: str = "*", labels: Iterable[str] = (), origin: str = "reviewer", note: str = "",
                 source: str = "", filename: str | None = None, fmt: str | None = None) -> str | None:
        """Record a reviewer verdict (CON-8) or an adversary-loop miss (EVAL-4) in the memory.

        verdict: "attack" (confirmed attack) or "false_positive". Content comes from `content` (extracted the same
        way inspect() extracts it) or from the recent in-process text of `event_id`; only fingerprints are stored."""
        if content is not None:
            content = extract(content, fmt=fmt, filename=filename, source=source).text
        else:
            hit = self._recent.get(event_id or "")
            if hit is None:
                raise KeyError("event not in recent memory; pass the content instead")
            agent_id = hit[0] if agent_id == "*" and verdict == "false_positive" else agent_id
            content = hit[1]
        kind = {"attack": "attack", "false_positive": "benign"}[verdict]
        return self.memory.add(content, kind, labels, agent_id=agent_id, origin=origin, note=note)

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
        unjudged: list[tuple[int, int]] = []
        oversize_hold = False
        key = self._key("scan", hashlib.sha256(content if isinstance(content, bytes) else content.encode()).hexdigest(),
                        source, filename, fmt)
        scan = self._get(key)
        too_large = len(content) > 4 * self.max_text_chars   # CORE-16 input limit (raw size, before any parsing)
        if too_large:
            scan = _Scan(ExtractedDoc(fmt or "text"), "", [], [])
            scan.doc.warnings.append("content too large to inspect")
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
        too_large = too_large or len(scan.doc.text) > self.max_text_chars
        findings = [f.model_copy(deep=True) for f in scan.findings]
        if scan.doc.warnings:
            degraded = True
            findings.append(Finding(signal="extraction-unavailable", labels=["Indirect Prompt Injection"]))
        if source == "user":
            session.note_trusted(scan.doc.text)
        else:
            session.note_untrusted(scan.doc.text)
            session.flagged_untrusted |= bool(scan.chunks or scan.doc.warnings)
        known: Match | None = None
        if policy.memory.enabled and source != "system" and scan.doc.text:
            known = self.memory.match(scan.doc.text, agent_id, policy.memory.match_threshold)
        if known is not None and known.kind == "attack":
            # Reviewer-confirmed attack: decided by rules at Tier 0, no AI call needed.
            findings.append(Finding(signal="known-attack:" + known.id, labels=known.labels or (
                ["Instruction Override"] if source == "user" else ["Indirect Prompt Injection"]), score=known.score))
            if source != "user":
                session.flagged_untrusted = True
        elif known is not None:
            pass   # reviewer-marked false positive: skip the AI tiers; structural rules below still apply
        elif scan.chunks:
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
            assessment, budget_degraded, unjudged = await self._judge(scan, source, session.task or policy.task_scope,
                                                                      policy, agent_id)
            degraded |= assessment.degraded
            if unjudged:   # structurally flagged chunks beyond the judge's window cap: never cleared unjudged
                findings.append(Finding(signal=f"judge-coverage-partial:{len(unjudged)}-chunks",
                                        labels=["Indirect Prompt Injection"] if source != "user" else ["Instruction Override"]))
                oversize_hold = True
        elif scan.all_chunks and source != "system":
            # No structural signal: Tier 1 scores every chunk; only chunks at or above the policy's
            # escalation threshold go to the Tier 2 judge (D-011: the classifier never decides alone).
            tier = 1
            score_key = self._key("scores-all", key)
            scored = self._get(score_key)
            tier1_failed = False
            if scored is None:
                try:
                    # CORE-16: the budget grows with the document (measured ~0.7 s per 1,000-character chunk on CPU)
                    budget = min(self.tier1_max_s, self.tier1_timeout_s * 4 + self.tier1_per_chunk_s * len(scan.all_chunks))
                    scored = await asyncio.wait_for(self._scores(scan.all_chunks), budget)
                    self._put(score_key, scored)
                except Exception:
                    degraded = tier1_failed = True
                    scored = []
            low = policy.thresholds.escalate_band[0]
            if (policy.thresholds.judge_untrusted == "always" and source != "user"
                    and len(scan.doc.text.strip()) >= policy.thresholds.judge_min_chars):
                low = 0.0   # policy: every untrusted document is assessed by the judge (scores still logged)
            hot_spans = {(f.span, f.origin) for f in scored if f.score >= low}
            if tier1_failed:
                # Without Tier 1 nothing can clear the content on the fast path: every chunk goes to the judge, and
                # an unavailable judge then holds it (judge-unavailable-hold / budget-hold) instead of allowing it.
                hot_spans = {((c[0], c[1]), c[2]) for c in scan.all_chunks}
            if hot_spans:
                findings.extend(f.model_copy(deep=True) for f in scored if f.score >= low)
                # a copy: the scan object is cached and must keep its structural chunks only
                scan = replace(scan, chunks=[c for c in scan.all_chunks if ((c[0], c[1]), c[2]) in hot_spans])
                if source != "user":
                    session.flagged_untrusted = True
                tier = 2
                priority = {f.span: f.score for f in scored if f.span}
                assessment, budget_degraded, unjudged = await self._judge(
                    scan, source, session.task or policy.task_scope, policy, agent_id, priority)
                degraded |= assessment.degraded
                # Chunks beyond the judge's window cap: cleared only by a Tier 1 score below the escalation band
                # (the `classifier` rule); anything else there is held (CORE-16).
                band = policy.thresholds.escalate_band[0]
                unjudged_hot = [s for s in unjudged if tier1_failed or priority.get(s, 1.0) >= band]
                if unjudged:
                    findings.append(Finding(signal=f"judge-coverage-partial:{len(unjudged)}-chunks",
                                            labels=["Indirect Prompt Injection"] if source != "user" else ["Instruction Override"]))
                    oversize_hold = bool(unjudged_hot)
        judge_labels = sorted(k for k, score in assessment.categories.items() if k in ATTACK_TYPES and score > 0)
        judge_labels = judge_labels or (["Instruction Override"] if source == "user" else ["Indirect Prompt Injection"])
        if assessment.malicious > 0:   # a degraded window scores 0; the others still count
            findings.extend(self._judge_findings(scan, assessment, judge_labels))
        hidden = [(f.span[0], f.span[1]) for f in findings
                  if f.signal == "non-visible-content" and f.span and policy.sensitive_data.drop_non_visible]
        # Forged role / tool-call markers are removed by policy, except from source code, where they are legitimate.
        hidden += [(f.span[0], f.span[1]) for f in findings
                   if f.signal == "role-marker" and f.span and policy.sensitive_data.strip_role_markers
                   and scan.doc.format != "code"]
        risk = max(assessment.malicious,
                   policy.thresholds.neutralise if hidden else 0.0,
                   policy.thresholds.block if known is not None and known.kind == "attack" else 0.0)
        labels = sorted({label for f in findings for label in f.labels})
        session.add_risk(risk, labels)
        if too_large:
            decision, rule, reason = (Decision.BLOCK, "content-too-large",
                                      f"Content exceeds the inspection limit ({self.max_text_chars} characters)")
        elif scan.doc.warnings:
            decision, rule, reason = Decision.BLOCK, "extraction-failed", "Content could not be fully inspected"
        elif known is not None and known.kind == "attack":
            decision, rule, reason = (Decision.BLOCK, "known-attack-match",
                                      f"Matches a confirmed attack in memory (similarity {known.score:.2f})")
        elif risk >= policy.thresholds.block:
            decision, rule, reason = Decision.BLOCK, "content-risk-block", "Content risk reached the policy block threshold"
        elif session.risk >= policy.session.block_at:
            decision, rule, reason = Decision.BLOCK, "session-risk-block", "Accumulated session risk reached the block threshold"
        elif assessment.degraded and scan.chunks:
            decision, rule, reason = (Decision.BLOCK, "budget-hold" if budget_degraded else "judge-unavailable-hold",
                                      "Flagged content is held until it can be assessed")
        elif oversize_hold:
            decision, rule, reason = (Decision.BLOCK, "oversize-hold",
                                      "Flagged parts of a long document exceed what the judge can assess; held")
        elif session.risk >= policy.session.escalate_at:
            decision, rule, reason = Decision.ESCALATE, "session-risk-escalate", "Accumulated session risk requires review"
        elif hidden:
            only_markers = all(f.signal != "non-visible-content" for f in findings if f.span in hidden)
            decision, rule, reason = ((Decision.NEUTRALISE, "strip-role-markers", "Forged role/tool-call markers removed by policy")
                                      if only_markers else
                                      (Decision.NEUTRALISE, "drop-non-visible", "Non-visible content quarantined by policy"))
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
                                                  assessment.model, assessment.input_tokens, assessment.est_cost,
                                                  assessment.output_tokens)
        self._remember_recent(result.event_id, agent_id, scan.doc.text)
        if policy.taint.enabled and source != "user":   # CORE-17: where this content came from (fingerprints only;
            # the user's own words were recorded as trusted above)
            session.taint.observe(scan.doc.text, result.event_id or "", source, trusted=False,
                                  flagged=decision != Decision.ALLOW or risk >= policy.thresholds.neutralise)
        return result

    async def check_action(self, tool: str, args: dict[str, Any], agent_id: str,
                           session_id: str | None = None) -> ActionResult:
        async with self._agent_locks.setdefault(agent_id, asyncio.Lock()):
            policy, session = self._policy(agent_id), self._session(agent_id, session_id)
            result = action_guard.check_action(tool, args, policy, session, self._secrets)
            if result.decision == Decision.ESCALATE:
                approved = self.logger.take_approval(session.session_id, tool, args)
                if approved:   # a human approved this exact call (CON-9); approvals never override a BLOCK
                    pinned = action_guard.check_action(tool, args, policy.model_copy(update={"mode": "monitor"}),
                                                       Session(agent_id=agent_id, trusted=dict(session.trusted)),
                                                       self._secrets)
                    result = result.model_copy(update={
                        "decision": Decision.ALLOW, "enforced": Decision.ALLOW, "final_args": pinned.final_args,
                        "policy_rule": "human-approved", "notice": None,
                        "reason": f"approved by a reviewer (approval {approved}); was: {result.reason}"})
            result.event_id = self.logger.action(session.session_id, agent_id, tool, args, result, session.risk)
            self.store.execute("UPDATE sessions SET risk = ? WHERE id = ?", (session.risk, session.session_id))
            return result

    def inspect_sync(self, *args: Any, **kwargs: Any) -> InspectResult:
        return _sync(lambda: self.inspect(*args, **kwargs))

    def check_action_sync(self, *args: Any, **kwargs: Any) -> ActionResult:
        return _sync(lambda: self.check_action(*args, **kwargs))
