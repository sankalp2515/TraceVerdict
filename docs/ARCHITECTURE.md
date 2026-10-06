# Architecture

Working name: Agent Security Gateway (code namespace `asg`). PRD: `docs/11-PRD-complete.md`. Decisions: `docs/DECISIONS.md`.

**Principle: rules decide, AI advises.** Every decision is made by a deterministic policy rule. Classifiers and the
LLM judge produce signals; no AI signal alone can allow high-risk content or a high-risk action.

## 1. One engine, four surfaces

```
             Python SDK (embedded | remote)     Gateway API (/v1)     LLM Proxy (/proxy/v1)     Console
                         \                            |                      |                     /
                          +---------------------------+----------------------+--------------------+
                                                      |
                                              Core Engine (asg_core)
              inspect(content, source, agent, session)        check_action(tool, args, agent, session)
                                                      |
                                  decision log (SQLite) -> replay, decisions feed, scorecard, metrics
```

| Surface | Code | How an agent adopts it |
|---|---|---|
| Python SDK, embedded | `packages/sdk/asg_sdk/guard.py` | `Guard("agent")`, `guard.inspect(...)`, `@guard.tool()`, `guard.session(...)` |
| Python SDK, remote (SDK-6) | `asg_sdk/remote.py` | `Guard("agent", remote=URL, api_key=KEY)`: same API, decisions by the gateway |
| LangChain / LangGraph (SDK-7) | `asg_sdk/langchain.py` | `tools = guard.protect_tools(tools)` (8 added or changed lines in `examples/langgraph_agent`, two of them its own docstring) |
| Gateway API | `services/gateway/asg_gateway/app.py` | HTTP, any language; OpenAPI at `/docs` |
| LLM proxy | `services/gateway/asg_gateway/proxy.py` | one setting: `OPENAI_BASE_URL=<gateway>/proxy/<agent>/v1` (`examples/openai_agent`) |

All surfaces call `Engine.inspect` / `Engine.check_action` (CORE-1; `tests/test_sdk_surfaces.py` proves it per surface).

## 2. Inbound content: `Engine.inspect`

```
raw bytes/text
  -> extract (CORE-2)        text, HTML (comments, hidden elements, alt), PDF (invisible/off-page text, metadata),
                             DOCX (hidden runs), email (headers, parts, attachments), JSON, Markdown, code, images (OCR)
                             each segment marked visible / non-visible: "see what the model sees"
  -> normalise (CORE-3)      NFKC + ftfy, format characters removed, ASCII folding of look-alikes (detection views)
  -> decode (CORE-3)         base64/base64url, hex, Unicode tag characters, %-encoding, rot13 -> extra views
  -> memory (trainability)   reviewer-confirmed attack fingerprints -> rules block at Tier 0, no AI call
  -> Tier 0 structural       non-visible content, encoded runs, invisible/mixed-script characters
  -> Tier 1 classifier       local open classifier (ONNX) on every chunk; an escalation signal only (D-011)
  -> Tier 2 judge            DecisionModel (free LLMs via the router); content passed as data between random
                             boundary markers; no tools; returns probability, 9-type labels, evidence quotes
  -> policy (CORE-7)         named rules: extraction-failed, known-attack-match, content-risk-block,
                             session-risk-block, judge-unavailable-hold / budget-hold, session-risk-escalate,
                             drop-non-visible, judge-neutralise, allow
  -> neutraliser (CORE-8)    quarantine only the offending spans; wrap the rest in fresh untrusted-data markers
  -> decision log (CORE-10)  hashes + redacted previews only; secrets/canaries redacted; user refs hashed
```

When the judge is called: on any structural signal; on a Tier 1 score in the escalation band; and, for agents
whose policy sets `judge_untrusted: always` (agents with high-risk tools), on every untrusted document of at
least `judge_min_chars`. User turns and short tool output stay on the fast path. Reason: the open classifier is
near-binary and misses paraphrased third-party instructions (DEF-017, measured in docs/EVALUATION.md).

## 3. Actions: `Engine.check_action` (CORE-9)

Deterministic checks, worst result wins: tool allowed → pinned fields rewritten from trusted session context →
outbound scan (canaries, registered secrets, detect-secrets patterns) → recipient allow-list → URL domain
allow-list → sandbox paths → provenance (a high-risk target that appears only in untrusted content) → session risk.
`ESCALATE` creates a pending approval (CON-9). A reviewer approval lets the *same* call in the *same* session run
once (`human-approved`); approvals can never override a `BLOCK`.

## 4. Session risk (CORE-6)

Each content decision adds its risk to the session; risk decays per turn. Content that is individually allowed
can still escalate or block the session (`tests/test_engine.py::test_session_accumulation_decay_and_cached_scan`).
Action violations add risk too, and high-risk tools are held in a risky session.

## 5. Fail-safe, cost, modes

| Concern | Behaviour |
|---|---|
| Tier time budgets (CORE-12) | extraction, Tier 1, Tier 2 each bounded; failures mark `degraded` |
| Judge down / unparseable | flagged content is held (`judge-unavailable-hold`), never silently allowed |
| Budget cap (CORE-14) | rules continue; flagged content held (`budget-hold`, `budget_degraded`) |
| Extraction failure | `extraction-failed` → BLOCK; an empty parse of non-empty text falls back to raw text (DEF-016) |
| SDK failure policy (SDK-5) | write/send tools fail closed, read tools fail open (logged); remote inspection failure withholds content |
| Modes (CORE-15) | `monitor` logs the same decisions as `enforce` but does not enforce them |
| Caches | scan and judge results cached by content hash and context; enforcement and session state never cached |

## 6. LLM router (CORE-11)

`config/providers.yaml` + `config/models.yaml`: roles (agent, judge, proxy upstream, …) map to ordered
provider/model lists. Failover on 429/5xx/timeouts, circuit breaker, tokens-per-minute throttle, per-provider
daily budgets, response cache, usage and equivalent cost recorded per call. One key per provider; spare keys
are used only if a key is rejected (D-004).

## 7. Trainability (PRD §7.2) and review

`asg_core/memory.py`: confirmed attacks (reviewer `POST /v1/feedback`, adversary-loop misses) are stored as
keyed hashes of word 5-shingles, never as text. Later content whose shingles contain ≥ 60% of a stored attack
is blocked at Tier 0 (`known-attack-match`) without an AI call, including when it is embedded in a larger
document. False-positive marks are exact-content and per agent; they skip the AI tiers but never structural
rules or the action guard.

## 8. Gateway API

| Endpoint | Scope | PRD |
|---|---|---|
| `POST /v1/inspect`, `POST /v1/actions/check`, `POST /v1/sessions` | project | API-1..3 |
| `GET /v1/sessions/{id}/events`, `GET /v1/decisions` | public | API-3, API-4 |
| `GET /v1/scorecard/{agent}` (latest reports + summary with grid claim) | public | API-5 |
| `GET /v1/policies/{agent}`, `PUT /v1/policies/{agent}` (validated, versioned, atomic) | public / admin | API-6 |
| `GET /v1/costs`, `GET /v1/costs/{agent}` (incl. security/agent overhead ratio) | public | API-11, G7b |
| `GET /v1/approvals`, `POST /v1/approvals/{event_id}` | public / admin | CON-9 backend |
| `POST /v1/feedback`, `GET /v1/memory`, `DELETE /v1/memory/{id}` | admin / public / admin | CON-8 backend |
| `GET /v1/metrics` (decisions by rule/label, escalation rate, latency p50/p95 by tier, provider errors) | public | NFR observability |
| `GET /demo/scenarios`, `POST /demo/run` | public | API-7 |
| `POST /proxy/v1/chat/completions`, `POST /proxy/{agent}/v1/chat/completions` | project | PRX-1..5 |
| `GET /healthz` | open | API-10 |

Gateway self-security: API keys hashed at rest, scopes (public < project < admin), per-key rate limits, body size
limit, CORS restricted to the Console origin, agent ids validated (no path traversal into the policy directory),
request ids on every response and in a structured access log, secrets only from the environment.

## 9. Evaluation

```
promptfoo (MIT) / garak (Apache-2.0)  ->  attack cases (we never author attack text: D-005, D-014)
eval/promptfoo/build_suites.py        ->  each indirect payload delivered through every channel (incl. hidden text)
eval/targets/agent_target.py          ->  protection off | on (reference agent) | detect (content checkpoint only)
python -m asg_eval.summary            ->  eval/reports/<date>-summary.json + docs/EVALUATION.md (grid claim by §15 rule)
```

Outcomes are deterministic (EVAL-5): canary checks, sandbox outbox, executed tool calls. False positives are
measured on a development benign set and on a held-out benign set written before any tuning.

## 10. Data (SQLite, Postgres-portable)

`sessions`, `events`, `findings`, `decisions`, `actions`, `approvals`, `memory`, `llm_usage`, `llm_cache`.
No raw content is stored: content hash + redacted preview (or hash only with `ASG_STORE_PREVIEWS=0`).
