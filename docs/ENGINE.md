# Engine decision flow

`asg_core.engine.Engine` is the shared SDK/API/proxy boundary. It uses the existing
extractor, normaliser, session registry, action guard, judge interface, router and
decision logger. Model/provider configuration stays in the existing YAML loaders;
all decision thresholds come from `AgentPolicy`.

Inspection rules run in this order; the first match wins. Requirement IDs link to
[PRD §8.1](11-PRD-complete.md#81-core-engine-core).

| `policy_rule` | When it fires | Effect | PRD IDs |
|---|---|---|---|
| `extraction-failed` | Extraction warns, fails or exceeds its time budget | BLOCK; record degraded inspection | CORE-1, CORE-10, CORE-12 |
| `content-risk-block` | Judge risk or mandatory hidden-content quarantine risk reaches `thresholds.block` | BLOCK | CORE-5, CORE-7 |
| `session-risk-block` | Risk after turn decay and accumulation reaches `session.block_at` | BLOCK | CORE-6, CORE-7 |
| `budget-hold` | Flagged content needs an uncached assessment and the agent's daily Tier 2 input-token budget is exhausted | BLOCK; `degraded` and `budget_degraded` | CORE-12, CORE-14 |
| `judge-unavailable-hold` | Flagged content cannot obtain a valid assessment before the Tier 2 deadline | BLOCK; `degraded` | CORE-7, CORE-12 |
| `session-risk-escalate` | Accumulated risk reaches `session.escalate_at` | ESCALATE; hold content for review | CORE-6, CORE-7 |
| `drop-non-visible` | Extracted hidden spans exist and `drop_non_visible` is enabled | NEUTRALISE those spans, independent of classifier/judge clearance | CORE-7, CORE-8 |
| `judge-neutralise` | Judge risk reaches `thresholds.neutralise` | NEUTRALISE evidence spans | CORE-5, CORE-7, CORE-8 |
| `allow` | No preceding rule matches | ALLOW the original text or extracted document view | CORE-1, CORE-7 |

Action decisions delegate unchanged to `action_guard.check_action`; all are logged.
The guard chooses the most restrictive observation (BLOCK before ESCALATE before
ALLOW), retaining its first rule when severity ties.

| `policy_rule` | When it fires | Effect | PRD IDs |
|---|---|---|---|
| `tool-not-allowed` | Unknown tool with `unknown_tools: block` | BLOCK | CORE-9 |
| `pinned-field-override` | Proposed pinned value differs from trusted session context | Rewrite and ALLOW unless another rule holds the action | CORE-9 |
| `outbound-secret` | Arguments contain a protected value or credential | BLOCK | CORE-9, CORE-10 |
| `recipient-not-allowed` | Recipient violates the tool's allow-list | BLOCK | CORE-9 |
| `domain-not-allowed` | URL violates the tool's domain allow-list | BLOCK | CORE-9 |
| `path-outside-sandbox` | Path leaves the workspace | BLOCK | CORE-9 |
| `target-from-untrusted-content` | A high-risk action targets an entity known only from untrusted content | ESCALATE when configured, otherwise BLOCK | CORE-6, CORE-9 |
| `high-risk-tool-in-risky-session` | A high-risk tool meets session escalation/block thresholds | ESCALATE or BLOCK | CORE-6, CORE-9 |
| `allow` | No guard violation | ALLOW | CORE-9 |

## Detection, containment and operations

Tier 0 extracts and normalises all segments. Non-visible text, normaliser flags and
encoded-looking runs select short segments for Tier 1; ordinary Unicode repair is
recorded without forcing escalation. No phrase signatures are embedded. Every
structurally flagged input goes to Tier 2 for resolution; classifier probabilities
are logged as advice and never enter final risk (D-011, D-013, D-015, D-016).
A failed Tier 1 is marked degraded and can still be resolved by a healthy judge.
Unresolved structural suspicion is held, as agreed for this implementation.

Risk is the judge probability, with a floor at `thresholds.neutralise` when hidden
content must be dropped. Each inspection decays the session then adds that risk;
action risk updates remain owned by the guard. Session ownership is checked before
state updates. Caller-supplied tasks and user-channel entities enter trusted
context; other channels enter provenance tracking.

Quarantine uses offsets in extracted text, merges overlaps and preserves remaining
text. Exact judge quotes map to every matching original span; unmatched or
transformed evidence falls back to the flagged original chunks, never guessed
normalised offsets. Fresh data boundaries wrap neutralised content. Monitor mode
records identical policy decisions but enforces ALLOW; action pinned-field behavior
remains the existing guard's behavior.

Constructor options bound Tier 0/1/2 work, classifier segment size, encoded-run
length and a shared in-memory LRU cache with TTL. Synchronous CPU work runs in a
worker thread; its timeout stops waiting but cannot terminate the worker. No
failed scan/assessment is cached. Assessment keys include content hash, source,
task, agent and policy. Cache hits cost zero and still recompute decisions, risk
and logging. Cached content stays in process; raw judge evidence is not persisted.

Agent/day budget admission uses input-token totals from persisted decision records
(UTC day); cached assessments remain available at the cap. Concurrent calls within
one engine serialize per agent through logging. The existing `Assessment` contract
reports input tokens only: a call admitted below the cap may cross it, and output
tokens are accounted by the router rather than this agent ledger. Separate engine
instances do not share admission locks. Clean Tier 0 inspections remain available
at the cap.

`register_secrets` adds runtime values to outbound checks and log redaction; policy
canaries register before session/task logging. A small compatible logger addition
redacts metadata as well as previews, including when previews are disabled. All
inspection/action decisions receive event IDs. Sync wrappers reject a running
event loop with instructions to await the async method.

Tests inject `StaticDecisionModel` and fake scorers, using neutral marker text and
benign documents. They require no model downloads or network access.
