# Architecture

Product: IntentSeal (code: `intentseal` SDK, `intentseal_core`, `intentseal_gateway`, `intentseal_eval`). PRD: `docs/11-PRD-complete.md`. Decisions: `docs/DECISIONS.md`.

**Principle: rules decide, AI advises.** Every decision is made by a deterministic policy rule. Classifiers and the
LLM judge produce signals; no AI signal alone can allow high-risk content or a high-risk action.

## 1. One engine, four surfaces

```
             Python SDK (embedded | remote)     Gateway API (/v1)     LLM Proxy (/proxy/v1)     Console
                         \                            |                      |                     /
                          +---------------------------+----------------------+--------------------+
                                                      |
                                              Core Engine (intentseal_core)
              inspect(content, source, agent, session)        check_action(tool, args, agent, session)
                                                      |
                   decision log (SQLite or PostgreSQL) -> replay, decisions feed, scorecard, metrics, SIEM export
```

| Surface | Code | How an agent adopts it |
|---|---|---|
| Python SDK, embedded | `packages/sdk/intentseal/guard.py` | `Guard("agent")`, `guard.inspect(...)`, `@guard.tool()`, `guard.session(...)` |
| Python SDK, remote (SDK-6) | `intentseal/remote.py` | `Guard("agent", remote=URL, api_key=KEY)`: same API, decisions by the gateway |
| LangChain / LangGraph (SDK-7) | `intentseal/langchain.py` | `tools = guard.protect_tools(tools)` (8 added or changed lines in `examples/langgraph_agent`, two of them its own docstring) |
| Gateway API | `services/gateway/intentseal_gateway/app.py` | HTTP, any language; OpenAPI at `/docs` |
| LLM proxy, OpenAI-compatible | `services/gateway/intentseal_gateway/proxy.py` | one setting: `OPENAI_BASE_URL=<gateway>/proxy/<agent>/v1` (`examples/openai_agent`); streaming supported (PRX-6) |
| LLM proxy, Anthropic Messages | same | one setting: `ANTHROPIC_BASE_URL=<gateway>/proxy/<agent>/anthropic`; native pass-through, streaming supported |
| Onboarding | `services/gateway/intentseal_gateway/setup.py`, Console **Set up** | register from a template, copy the connection, run the self-test (docs/INTEGRATION.md) |

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
  -> Tier 0 structural       non-visible content, encoded runs, invisible/mixed-script characters, forged role /
                             tool-call markers (chat-template tokens; stripped by policy, source code exempt)
  -> Tier 1 classifier       local open classifier (ONNX) on every chunk; an escalation signal only (D-011)
  -> Tier 2 judge            DecisionModel (free LLMs via the router); content passed as data between random
                             boundary markers; no tools; returns probability, 9-type labels, evidence quotes.
                             Long documents are judged in windows (CORE-16, below)
  -> policy (CORE-7)         named rules: extraction-failed, known-attack-match, content-risk-block,
                             session-risk-block, judge-unavailable-hold / budget-hold, oversize-hold,
                             session-risk-escalate, drop-non-visible, judge-neutralise, allow; content-too-large first
  -> neutraliser (CORE-8)    quarantine only the offending spans; wrap the rest in fresh untrusted-data markers
  -> decision log (CORE-10)  hashes + redacted previews only; secrets/canaries redacted; user refs hashed
```

When the judge is called: on any structural signal; on a Tier 1 score in the escalation band; and, for agents
whose policy sets `judge_untrusted: always` (agents with high-risk tools), on every untrusted document of at
least `judge_min_chars`. User turns and short tool output stay on the fast path. Reason: the open classifier is
near-binary and misses paraphrased third-party instructions (DEF-017, measured in docs/EVALUATION.md).
If Tier 1 itself fails (model not loaded, timeout), nothing can clear content on the fast path: every chunk goes
to the judge, and an unavailable judge holds it (audit F3, D-039).

**Long documents (CORE-16, D-041).** A document whose detection view fits one judge window (6,000 characters) is
judged whole, with its context. A longer one is judged as windows of its flagged chunks, in document order, at
most `INTENTSEAL_JUDGE_MAX_WINDOWS` (8) windows, most suspicious first. Evidence quotes are located in the
original text inside the windows judged malicious, so quarantine spans are exact original offsets; a quote that
is not verbatim quarantines only that window's chunks. Chunks beyond the window cap are cleared only by a Tier 1
score below the escalation band, otherwise the document is held (`oversize-hold`). Tier 1's time budget grows
with the document (about 0.7 s per 1,000-character chunk on CPU). Text over `INTENTSEAL_MAX_TEXT_CHARS` is
refused (`content-too-large`). Measured on CPU: 25 KB of HTML fully inspected in 12 s; ~100 KB and larger is held.

## 3. Actions: `Engine.check_action` (CORE-9)

Deterministic checks, worst result wins: tool allowed → pinned fields rewritten from trusted session context →
outbound scan (canaries, registered secrets, detect-secrets patterns) → recipient allow-list → URL domain
allow-list → sandbox paths → provenance (a high-risk target that appears only in untrusted content) → session risk
→ explicit intent (`intent_terms`: a high-risk action the user's own words never ask for is escalated; the
confused-deputy lesson, docs/13) → data flow (CORE-17, below). The outbound scan also reads decoded views of every
argument (base64, hex, %-encoding, reversed, tag characters). Allow-lists use the host and addresses a real client would use (`urlsplit`,
`email.utils.getaddresses`): fragment, user-part, backslash and display-name tricks fail (audit F1/F2, D-039).
`ESCALATE` creates a pending approval (CON-9). A reviewer approval lets the *same* call in the *same* session run
once (`human-approved`); approvals can never override a `BLOCK`.

**Data flow / taint (CORE-17, D-042).** Every inspected piece of untrusted content is remembered per session as
a fingerprint (hashed word 5-shingles, no text) with its origin (source channel, event id, flagged or not); the
user's own words are recorded as trusted and never count as taint. Each string argument of a tool call is traced
to its origins; text copied from flagged content into a high-risk tool is escalated (policy `taint.flagged_to_high_risk`:
escalate | block | record), and every traced flow is returned with the decision and stored for replay.

## 4. Session risk (CORE-6)

Each content decision adds its risk to the session; risk decays per turn. Content that is individually allowed
can still escalate or block the session (`tests/test_engine.py::test_session_accumulation_decay_and_cached_scan`).
Action violations add risk too, and high-risk tools are held in a risky session.

## 5. Fail-safe, cost, modes

| Concern | Behaviour |
|---|---|
| Tier time budgets (CORE-12) | extraction, Tier 1, Tier 2 each bounded; failures mark `degraded` |
| Judge down / unparseable | flagged content is held (`judge-unavailable-hold`), never silently allowed |
| Tier 1 down / timed out | every chunk goes to the judge; judge also down → held. A failed classifier load is retried every 60 s and reported by `/readyz` |
| Unknown agent id | the Gateway answers 404 instead of running the default (monitor) policy; the SDK warns when it falls back to monitor mode |
| Budget cap (CORE-14) | rules continue; flagged content held (`budget-hold`, `budget_degraded`) |
| Extraction failure | `extraction-failed` → BLOCK; an empty parse of non-empty text falls back to raw text (DEF-016) |
| SDK failure policy (SDK-5) | write/send tools fail closed, read tools fail open (logged); remote inspection failure withholds content |
| Modes (CORE-15) | `monitor` logs the same decisions as `enforce` but does not enforce them |
| Caches | scan and judge results cached by content hash and context; enforcement and session state never cached |

## 6. Model providers

Two separate questions, both provider-neutral:

- **The gateway's own model calls** (judge, demo agent, default proxy upstream) go through the router (below). Adapters:
  `openai_compatible` (OpenAI, Azure with an `api-key` header, Gemini, Groq, Mistral, OpenRouter, NVIDIA, DeepSeek, xAI,
  Together, local servers with `no_auth`) and `anthropic` (native Messages API through the official SDK, translated to
  and from the router's OpenAI shape, streaming and tool use included).
- **An agent's own model calls through the proxy** follow its policy `upstream:` (provider, optional model override,
  `key: gateway | client`). `call_upstream` makes one call to that provider: no failover and no shared cooldown (the
  customer chose the provider, and a client key's rate limit is that client's); the provider's status code and
  `Retry-After` are returned to the client. The Anthropic endpoint forwards the client's Messages body natively when
  the upstream is Anthropic, and translates otherwise.

## 7. LLM router (CORE-11)

`config/providers.yaml` + `config/models.yaml`: roles (agent, judge, proxy upstream, …) map to ordered
provider/model lists. Failover on 429/5xx/timeouts, circuit breaker, tokens-per-minute throttle, per-provider
daily budgets, response cache, usage and equivalent cost recorded per call. One key per provider; spare keys
are used only if a key is rejected (D-004).

## 8. Trainability (PRD §7.2) and review

`intentseal_core/memory.py`: confirmed attacks (reviewer `POST /v1/feedback`, adversary-loop misses) are stored as
keyed hashes of word 5-shingles, never as text. Later content whose shingles contain ≥ 60% of a stored attack
is blocked at Tier 0 (`known-attack-match`) without an AI call, including when it is embedded in a larger
document. False-positive marks are exact-content and per agent; they skip the AI tiers but never structural
rules or the action guard.

## 9. Gateway API

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
| `POST /proxy/v1/chat/completions`, `POST /proxy/{agent}/v1/chat/completions` (streaming: text streams through, tool calls buffered, checked, then released) | project | PRX-1..6 |
| `GET /v1/export/decisions?since=&format=jsonl\|cef` (SIEM pull, resumable) | project | API-12 |
| `GET /v1/whoami` (scope, organisation, visible agents) | public | D-037 |
| `GET /v1/agents`, `GET /v1/providers`, `GET /v1/setup/templates`, `GET /v1/agents/{agent}/connect` | public | D-049 |
| `POST /v1/agents` (create from a template) | admin | D-049 |
| `POST /v1/agents/{agent}/self-test` | project | D-049 |
| `POST /proxy/{agent}/anthropic/v1/messages` (Anthropic Messages, streaming) | project | D-048 |
| `GET /healthz` (liveness), `GET /readyz` (database, policies, Tier 1 classifier; LLM providers reported) | open | API-10, B1 |

Gateway self-security: API keys hashed at rest, scopes (public < project < admin), per-key rate limits (the
public key also per client address), a global hourly cap on live demo runs, body size limit enforced while the body
streams in (before authentication), CORS restricted to the Console origin, agent ids validated (no path traversal
into the policy directory), request ids on every response and in a structured access log, secrets only from the
environment.

**Organisations (API-12, D-043).** An agent's policy names its organisation (`org`, default `default`); a key is
`name:key:scope[:org[:agent|agent]]` (org `*` = all). Every endpoint that names an agent, or reads decisions,
sessions, approvals, memory, metrics, costs or exports, is limited to the key's agents; others answer 404.
`INTENTSEAL_PUBLIC_AGENTS` narrows the public Console key to the demo agents. A deployment whose keys and policies
are all in the default organisation behaves as a single tenant.

**SIEM (API-12).** Decisions as ECS-style JSON Lines or CEF: pulled from `/v1/export/decisions`, or pushed by
`INTENTSEAL_SIEM_SINKS` to a rotating JSONL file, an HTTP webhook (batched, retried) or syslog, asynchronously
through a bounded queue (delivery counters in `/v1/metrics`). Records carry redacted reasons and scores, never
content or arguments.

## 10. Evaluation

```
promptfoo (MIT) / garak (Apache-2.0)  ->  attack cases (we never author attack text: D-005, D-014)
eval/promptfoo/build_suites.py        ->  each indirect payload delivered through every channel (incl. hidden text)
eval/targets/agent_target.py          ->  protection off | on (reference agent) | detect (content checkpoint only)
python -m intentseal_eval.summary            ->  eval/reports/<date>-summary.json + docs/EVALUATION.md (grid claim by §15 rule)
```

Outcomes are deterministic (EVAL-5): canary checks, sandbox outbox, executed tool calls. False positives are
measured on a development benign set and on a held-out benign set written before any tuning.

## 11. Data (SQLite or PostgreSQL)

`sessions`, `events`, `findings`, `decisions`, `actions` (incl. data-flow taint), `approvals`, `memory`,
`llm_usage`, `llm_cache`. SQLite by default; PostgreSQL with `INTENTSEAL_DATABASE_URL` (psycopg 3, optional extra
`intentseal-core[postgres]`). Application SQL is written once in a portable subset; the PostgreSQL store adapts
placeholders and table definitions in one place, and the storage contract tests run on both (CI starts PostgreSQL).
Schema changes are additive only, so an older image runs on a newer database (rollback).
No raw content is stored: content hash + redacted preview (or hash only with `INTENTSEAL_STORE_PREVIEWS=0`, the
Docker image default).

## 12. Deployment

`Dockerfile` (gateway; classifier baked in, uid 1000, `/data` volume, HEALTHCHECK on `/readyz`),
`docker-compose.yml` (optional PostgreSQL profile), `python -m intentseal_gateway` (one worker: sessions, rate limits
and proxy state are in process; scale with more containers on a shared PostgreSQL and session affinity).
Step-by-step guide, settings reference and operations runbook: `docs/DEPLOY.md`.
