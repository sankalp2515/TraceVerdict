# PRD v2.0 — Agent Security Gateway (complete implementation spec)

> **Status:** Draft for sign-off · **Date:** 5 Oct 2026 · **Owner:** Sankalp (solo), Claude as engineering team
> **Supersedes:** docs/07 (PRD v1). **Built on:** docs/05 (evidence), docs/06 (problem statement, ideation), docs/09 (system design), docs/10 (cost model, Jev), [architecture blueprint](https://claude.ai/artifact/5QZiq9CnMCynuZvrkmLAWb), [Miro board](https://miro.com/app/board/uXjVHL5XE9E=/).
> **Hard deadline:** ET AI Hackathon submission **Sat 11 Oct 2026, 11:59 PM IST**, via Unstop.
> **Model policy:** free tiers and local open models only. Paid models (e.g. Jev) are a later, pluggable option.
> **Working name:** "Agent Security Gateway" (final product name: open question Q1).

> **v2.1 change note (5 Oct, approved):** CORE-2b images via OCR is now **P0** (target D3, fallback D2);
> EVAL gains a **variant generator** (9 types × 11 sources coverage map); EVAL-4 adversary loop moves to
> second-to-last in the cut order; one key per provider with spares for emergencies only. Details and
> revised cut order: `docs/DECISIONS.md` D-004…D-008.

---

## 1. Summary

The Agent Security Gateway is a security layer that wraps any LLM-based agent. It inspects everything the agent reads, from every channel. It removes only the malicious part of that content, checks every action the agent tries to take, and records every decision so a security team can replay it.

It ships as one **Core Engine** with four ways to reach it:
- a **Python SDK** (deepest protection);
- a **Gateway API** (any language);
- an **LLM Proxy** (zero code changes);
- a **Security Console** web app (reviewers, builders, and the public demo).

**Promise:** catch what can be caught, limit what a hijacked agent can do, and prove what happened. We do **not** claim to "solve" prompt injection.

---

## 2. Problem statement

> Teams can't safely let their AI agents read content from outside (documents, web pages, emails, tool results), because hidden instructions in that content can take over the agent. Today's protections watch the wrong channel, miss reworded attacks, get switched off for false alarms, and leave no evidence of what happened.

Evidence: the 8 sourced quotes in docs/06 Part A; 75 sourced findings in `findings.csv`.

| Pain (real quote) | What the product must do |
|---|---|
| "Our prompt filter was watching the user input field, not the document upload." | Inspect every channel |
| "If the scanner flags these, developers will disable it within a day." | Low false alarms; monitor mode first |
| "Copilot apparently has classifiers for these, but… these can easily be defeated" | Layered, normalised, adaptive detection |
| "LLM-provided kwargs can still override partial_params" | Check actions; pin trusted fields |
| "On audit, 'we log tool calls' didn't survive contact." | Full decision log and session replay |
| "Users approve 93% of permission prompts." | Ask humans rarely, with a clear reason |
| "The hardest part isn't getting the agent to work… it's getting the security team comfortable" | Hand the reviewer measurable evidence |

---

## 3. Users

| Persona | Role | Primary job-to-be-done |
|---|---|---|
| **Builder** (primary user) | Agent developer / platform lead | Protect an existing agent without rebuilding it, without breaking it, and get it approved |
| **Reviewer** (approver/buyer) | Security / risk / compliance | Approve an agent on evidence; investigate incidents; set policy |
| **Judge / visitor** | Hackathon judges, senior reviewers | See the problem and the protection working in under 3 minutes |
| End user (indirect) | Uses the protected agent | Get work done safely, without unexplained refusals |

---

## 4. Goals and success metrics

| # | Goal | Metric | Success target | Stretch |
|---|---|---|---|---|
| G1 | Hidden instructions from any supported channel lose influence | Attack success rate (ASR) on the reference agent, protected vs. unprotected (static corpus) | ≥ 80% relative reduction | ≥ 95% |
| G2 | Hijacks don't become tool misuse or leaks | Canary secrets leaked across all scenarios | 0 | 0 |
| G3 | Builders keep it switched on | False-positive rate (FPR) on the hard-benign set | ≤ 5% | ≤ 2% |
| G3b | Legitimate work still gets done | Utility retention (benign task success, protected ÷ unprotected) | ≥ 90% | ≥ 97% |
| G4 | Reviewers can verify everything | Decisions with reason + source span | 100% | — |
| G4b | | Sessions fully replayable | 100% | — |
| G5 | Credible F3 claim | Detection recall per claimed attack type | ≥ 85% on ≥ 7 types | ≥ 95% |
| G6 | Robust against an attacker who adapts | ASR on adaptive/generated variants (reported separately) | Reported honestly, with trend | Falls each red-team round |
| G7 | Low overhead | Added latency, fast path, p95 | ≤ 300 ms | ≤ 100 ms |
| G7b | | Security cost ÷ agent model cost (free-tier usage converted at list price) | Reported | < 10% |
| G8 | Easy adoption | Lines changed to protect a second, unmodified agent | SDK ≤ 10 lines; proxy = 1 setting | — |

All numbers are reported as measured, from a reproducible evaluation run. Targets are hypotheses, not claims.

---

## 5. Non-goals

| Non-goal | Why |
|---|---|
| Claiming prompt injection is solved | Untrue; would be penalised as over-claiming |
| Agent identity/IAM provisioning | Separate category; we enforce at the action boundary |
| Vetting MCP servers or skill registries before install | Separate initiative; runtime tool descriptions are in scope as an input channel |
| Non-adversarial multi-tenant mix-ups | Real pain, but not prompt injection |
| General toxicity/content moderation | Not among the 9 attack types |
| SDKs beyond Python; MCP traffic proxy | Time; roadmap |
| Training our own foundation model | Time; we use rules + open classifiers + free LLM judges |
| Paid models in the MVP (incl. Jev) | Budget; kept as a pluggable slot (§21) |
| Real email/payment/external side effects in the demo | Safety; all outbound actions are sandboxed |

---

## 6. Product overview

| Surface | Form | Who | Hackathon role |
|---|---|---|---|
| **Core Engine** | Python library | Internal; used by every other surface | The firewall itself |
| **Python SDK** | Python package | Builders | Deep integration demo |
| **Gateway API** | FastAPI service (Docker) | Any language; Console backend | "Fits any system" |
| **LLM Proxy** | OpenAI-compatible endpoint in the same service | Any agent, zero code | "Drop-in" proof |
| **Security Console** | React web app (static) | Reviewers, builders, judges | **Public demo link** |
| **Reference Research Agent** | LangGraph agent with tools | Demo and evaluation target | The agent we protect |
| **Evaluation & Red-team harness** | CLI + datasets | Engineering | Evidence for the grid claim |

---

## 7. Hackathon compliance matrix

### 7.1 Rules

| Rule (source) | How we comply |
|---|---|
| Submit via Unstop "Submit" before deadline; late rejected (FAQ) | Target submission evening of 11 Oct; buffer day |
| GitHub repo, demo video and documentation publicly accessible and properly named (FAQ, microsite) | Public repo; public Console link; public video link; checklist §19 |
| Working prototype (GitHub URL), pitch deck (PDF/PPT), 2–4 min video (Unstop) | §19 |
| All code and assets original and developed during the hackathon (microsite) | Fresh repo; no Veriscope code; third-party libraries and models credited |
| Open-source tools, libraries, datasets, models permitted (microsite) | Free/open models; dataset licences checked before inclusion |
| Plagiarism / misconduct = disqualification | Credits and licences listed in README |
| Self-declare F/D position; penalties for over- **and** under-estimating (PDF) | Claim rule in §15 |
| Working demo across all claimed areas + detailed structural architecture (PDF) | Demo scenarios §16; architecture doc §19 |

### 7.2 Problem-2 requirements

| PDF requirement | Requirement IDs |
|---|---|
| "Intercepts all incoming content before it influences the AI's behavior" | CORE-1, SDK-2, PRX-2 |
| "Detect and neutralize malicious instructions… in user input or retrieved data" | CORE-3…CORE-8 |
| "Allowing legitimate content to pass with minimal disruption" | CORE-7, G3, G3b, monitor mode |
| Input sources: user messages, web pages, PDFs, emails, Markdown, HTML, Word, API responses, OCR text, source code, images via OCR | CORE-2 |
| 9 attack types (F1 ≥2, F2 ≥5, F3 ≥7) | §14 coverage matrix, CORE-5 |
| Depth D1–D3 (input heterogeneity + demonstrated reliability) | §15 |
| Supporting features: observability, trainability, fault tolerance | CORE-10, EVAL-4, CORE-12 |

### 7.3 Judging criteria

| Criterion (PDF 8 + microsite 6) | Where we show it |
|---|---|
| Significance / relevance | Real-pain problem statement; OWASP LLM01 / ASI01 |
| Innovation / originality | Action checkpoint + span-level neutralisation + evidence layer + self-testing loop, versus classifier-only tools |
| Effective use of AI | Tiered AI detection; AI red-team agent |
| Technical complexity and execution | Five surfaces, one engine, measured |
| Agentic / autonomous capability | Tiered investigation, task-aware action checks, adversary loop, graduated response |
| Business / user impact; business viability | Unblocks security review; cost overhead metric |
| Prototype quality and usability; presentation | Public Console; 3-minute video |
| Scalability, responsible AI, robustness | Rules-decide principle, fail-safe, privacy, human oversight, honest metrics |

---

## 8. Functional requirements

Priorities: **P0** = must ship · **P1** = include if time allows · **P2** = design for, build later.

### 8.1 Core Engine (CORE)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CORE-1 | P0 | **Single inspection entry point.** `inspect(content, source, agent_id, session_id)` used by every surface | All surfaces call it; a test per surface proves no bypass |
| CORE-2 | P0 | **Content extraction ("see what the model sees").** Text, Markdown, HTML (incl. comments, hidden elements, alt text), PDF (incl. non-visible text, metadata, annotations), DOCX, email (headers + body + attachments), JSON/API responses, source code (incl. comments). Images via OCR is P1 (CORE-2b) | Per-format tests; hidden content appears in the extracted view and is flagged as non-visible |
| CORE-3 | P0 | **Normalisation.** Unicode normalisation, invisible-character stripping, decoding common encodings, homoglyph folding; records every transformation | Encoded-instruction test cases decode before scoring; the original content given to the agent is unchanged except for neutralised spans |
| CORE-4 | P0 | **Tiered detection.** Tier 0 rules/signatures (all content); Tier 1 local open classifiers; Tier 2 AI judge via the `DecisionModel` interface (free LLMs now) | Clean content finishes at Tier 0/1; tier used is logged; escalation rate is measured |
| CORE-5 | P0 | **Attack-type labelling.** Every finding labelled with ≥1 of the 9 types | Labels on 100% of findings; per-type metrics computable |
| CORE-6 | P0 | **Session risk.** Per-session risk accumulates across turns, with decay | Multi-step scenarios caught where no single turn is flagged |
| CORE-7 | P0 | **Policy engine (deterministic).** Combines all signals + agent policy into ALLOW / NEUTRALISE / BLOCK / ESCALATE. No AI signal alone can produce ALLOW for high-risk content | Every decision traceable to a policy rule; unit tests per rule |
| CORE-8 | P0 | **Span-level neutraliser.** Quarantine only malicious spans; wrap the remaining untrusted content in data markers | Utility tests pass; quarantined spans are recorded |
| CORE-9 | P0 | **Action guard.** `check_action(tool, args, agent_id, session_id, task)`: allowed-tool check, task-fit check, pinned trusted fields, outbound secret/credential/canary scan | Off-task tool calls blocked; pinned fields overridden; canaries never leave |
| CORE-10 | P0 | **Decision logger.** Every decision stores source, extracted span, labels, scores, tier, policy rule, action, latency, cost, model, `degraded` flag. Secrets are **redacted** in logs | 100% decisions logged; no raw secret values in the store |
| CORE-11 | P0 | **LLM router.** Free providers (Groq, Gemini, OpenRouter free models, Mistral, NVIDIA) from config; failover; response cache; quota tracking | Killing one provider in a test still yields decisions |
| CORE-12 | P0 | **Fail-safe.** Per-tier time budgets; AI tier failure → rules-only decision marked `degraded`; high-risk never passes silently | Fault-injection tests |
| CORE-13 | P0 | **`DecisionModel` interface (pluggable AI judge).** Typed questions in, typed answers + probabilities out. Adapters: generative free LLM (MVP). **Jev adapter slot reserved (§21)** | Swapping adapters needs config only; adapter contract tests |
| CORE-14 | P0 | **Cost controls.** Per-decision cost record; content-hash cache; per-agent/day budgets; safe behaviour at cap | Budget-exceeded test → rules continue, high-risk held, flagged `budget_degraded` |
| CORE-15 | P0 | **Modes.** `monitor` (log only) and `enforce` per agent | Same inputs give identical decisions in both modes; only enforcement differs |
| CORE-16 | P1 | Input limits (max size, chunking for long documents with span mapping) | Large-document test passes without timeouts |
| CORE-2b | P1 | Images via OCR (local, open-source) | Image test cases inspected via extracted text |
| CORE-17 | P2 | Origin/taint tracking through the agent's data flow | — |

### 8.2 Python SDK (SDK)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| SDK-1 | P0 | `Guard(agent, policy, mode)` client, embedded mode (engine in-process) | Reference agent protected in embedded mode |
| SDK-2 | P0 | `guard.inspect(raw, source=…)` for content loaders (files, web, email, retrieval) | All reference-agent channels routed through it |
| SDK-3 | P0 | `@guard.tool(pinned={...})` decorator for tool calls | Off-task / pinned-field / outbound tests pass |
| SDK-4 | P0 | `guard.session(user_id, task)` context: trusted fields and task | Session risk and task-fit use it |
| SDK-5 | P0 | Per-tool failure policy: write/send tools fail closed, read-only tools fail open (logged) | Fault-injection test |
| SDK-6 | P1 | Remote mode (calls the Gateway API) | Same decisions as embedded mode |
| SDK-7 | P1 | LangGraph/LangChain tool wrapper helper | A second sample agent protected with ≤ 10 changed lines |
| SDK-8 | P2 | JS/TS SDK | — |

### 8.3 Gateway API (API)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| API-1 | P0 | `POST /v1/inspect` | Returns decision, cleaned content, findings, `degraded` |
| API-2 | P0 | `POST /v1/actions/check` | Returns decision, final args, reason |
| API-3 | P0 | `POST /v1/sessions`, `GET /v1/sessions/{id}/events` | Ordered events for replay |
| API-4 | P0 | `GET /v1/decisions?filter=…` | Filter by decision, label, agent, time |
| API-5 | P0 | `GET /v1/scorecard/{agent}` | Latest evaluation metrics |
| API-6 | P0 | `GET /v1/policies/{agent}` (read); `PUT` admin-only (P1) | Policy served from YAML |
| API-7 | P0 | `POST /demo/run` (scenario × protection on/off) for the Playground | Runs the reference agent in a sandbox |
| API-8 | P0 | Auth: API key per project; public read-only demo key for Console | Unauthorised requests rejected |
| API-9 | P0 | Rate limiting and request size limits | Protects free quotas and the host |
| API-10 | P0 | `GET /healthz`; OpenAPI docs | Health checks pass on host |
| API-11 | P1 | `GET /v1/costs/{agent}` | Cost panel data |
| API-12 | P2 | SIEM export, multi-tenant orgs, Postgres | — |

### 8.4 LLM Proxy (PRX)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| PRX-1 | P0 | OpenAI-compatible `POST /proxy/v1/chat/completions` (incl. tools) | An unmodified sample agent works by changing only its base URL |
| PRX-2 | P0 | Inspect user and tool messages before forwarding; neutralise in place | Indirect-injection scenario through tool results is caught |
| PRX-3 | P0 | Check each returned tool call; replace blocked calls with a safe notice; enforce pinned fields | Blocked tool call never reaches the agent |
| PRX-4 | P0 | Upstream via the LLM router (≥ 2 free providers) | Works on two providers |
| PRX-5 | P0 | Agent and session identification via headers (`X-Agent-Id`, `X-Session-Id`) | Decisions grouped correctly |
| PRX-6 | P1 | Streaming: buffer tool-call chunks until complete, check, then release; text streams through | Streamed tool call is checked |
| PRX-7 | P2 | MCP traffic proxy; other API formats | — |

### 8.5 Security Console (CON)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| CON-1 | P0 | **Playground**: pick a scenario, run with protection OFF then ON, side by side; show sandboxed outbox and "canary leaked: yes/no" | Every demo scenario runs live from the public link |
| CON-2 | P0 | **Session replay**: timeline of content in → finding → decision → action; span highlighting; labels; tier; rule | Any session replayable |
| CON-3 | P0 | **Scorecard**: recall per attack type, FPR, utility retention, latency, ASR static vs adaptive, F/D claim with date of run | Rendered from the latest evaluation |
| CON-4 | P0 | **Decisions feed**: filter by decision/label/agent | Works on live data |
| CON-5 | P0 | Clear status banner when backend is unavailable or degraded | Tested |
| CON-6 | P1 | Cost panel (CORE-14 data) | Renders spend per tier/agent |
| CON-7 | P1 | Policy view (read-only); edit with admin key | — |
| CON-8 | P1 | Mark false positive / confirm attack (admin) | Feeds the regression set |
| CON-9 | P1 | Approvals inbox for ESCALATE decisions, with full action details in plain language | — |
| CON-10 | P0 | Responsive, accessible (keyboard, contrast), light/dark | Spot-checked |

### 8.6 Reference Research Agent (REF)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| REF-1 | P0 | LangGraph research assistant on a free tool-calling model | Completes benign tasks unprotected and protected |
| REF-2 | P0 | Tools: `web_fetch` (from a local fixture site, not the open web), `read_file` (PDF/DOCX/HTML/MD/email/image), `query_db` (SQLite with synthetic customers), `write_file` (sandbox dir), `send_message` (sandboxed outbox; never real email) | All tools sandboxed |
| REF-3 | P0 | Planted canary secrets (fake API key, fake customer data) | Canary leakage measurable |
| REF-4 | P0 | Built fresh for the hackathon (originality) | — |

### 8.7 Evaluation and red-team harness (EVAL)

| ID | Pri | Requirement | Acceptance criteria |
|---|---|---|---|
| EVAL-1 | P0 | **Corpus**: attack cases covering 9 types × supported channels, built from licensed public datasets plus our own synthetic cases; **hard-benign set** (security articles, code, ordinary "ignore my last email" style messages) | Each case labelled with type, channel, expected outcome |
| EVAL-2 | P0 | **Runner**: one command computes ASR (unprotected vs protected), recall/type, FPR, utility retention, latency p50/p95, cost | Reproducible; results file versioned |
| EVAL-3 | P0 | **Report** (Markdown + JSON) feeding the Scorecard | Generated automatically |
| EVAL-4 | P1 | **Adversary loop**: a red-team agent generates variants against the gateway; misses become regression cases; per-round metrics | ≥ 1 round with before/after numbers |
| EVAL-5 | P0 | Success measured deterministically (canary checks, tool-call logs), not by an LLM opinion | — |
| EVAL-6 | P2 | Jev comparison run (§21) | — |

---

## 9. Policy model (per agent, YAML)

```yaml
agent: research-agent
mode: monitor            # monitor | enforce
task_scope: "Answer research questions using the user's files, the database and approved web sources."
tools:
  read_file:     { risk: low,  failure: open }
  web_fetch:     { risk: low,  failure: open }
  query_db:      { risk: medium, failure: closed, pinned: [customer_id] }
  write_file:    { risk: medium, failure: closed }
  send_message:  { risk: high, failure: closed, escalate_if_uncertain: true,
                   allowed_recipients: ["@example-corp.test"] }
sensitive_data:
  patterns: [api_key, credential, customer_record]
  canaries: from_env
thresholds:
  neutralise: 0.6
  block: 0.85
  escalate_band: [0.5, 0.85]   # only for high-risk tools
session:
  risk_decay_per_turn: 0.2
  block_at: 1.5
budgets:
  daily_tokens_tier2: 200000
  on_exceeded: rules_only_hold_high_risk
decision_model: generative_free   # later: jev (see §21)
```

---

## 10. Data model (SQLite in MVP; Postgres-portable)

| Entity | Key fields |
|---|---|
| `agents` | id, name, policy_version, mode |
| `sessions` | id, agent_id, user_ref (hashed), task, started_at, risk_score |
| `events` | id, session_id, seq, kind (content_in / action / decision / escalation), source/channel, content_hash, created_at |
| `findings` | id, event_id, span_start, span_end, span_preview (redacted), labels[], scores{}, tier |
| `decisions` | id, event_id, decision, policy_rule, reason, latency_ms, degraded, budget_degraded, model, input_tokens, est_cost |
| `actions` | id, event_id, tool, args_redacted, final_args_redacted, pinned_overrides |
| `eval_runs` | id, git_sha, corpus_version, model_config, metrics{}, created_at |
| `cache` | content_hash, decision_payload, expires_at |

Privacy rules: user references hashed; secrets and canary values never stored in plain text; raw content stored only as hash + redacted preview in public demo mode.

---

## 11. API contract (summary)

```
POST /v1/inspect          {content|file, source, agent_id, session_id}
  → {decision, cleaned_content, findings:[{span, labels, scores, tier}], degraded, latency_ms}

POST /v1/actions/check    {tool, args, agent_id, session_id}
  → {decision, final_args, reason, labels, degraded}

POST /v1/sessions         {agent_id, user_ref, task} → {session_id}
GET  /v1/sessions/{id}/events → [ordered events with findings and decisions]
GET  /v1/decisions?decision=&label=&agent=&since=
GET  /v1/scorecard/{agent}
GET  /v1/policies/{agent}
POST /demo/run            {scenario_id, protection: on|off} → {transcript, outbox, canary_leaked, session_id}
POST /proxy/v1/chat/completions   (OpenAI-compatible; headers X-Agent-Id, X-Session-Id)
GET  /healthz
```

---

## 12. Non-functional requirements

| Area | Requirement |
|---|---|
| **Performance** | Fast path (Tier 0/1) p95 ≤ 300 ms per inspection on the free host; Tier 2 bounded by a per-call time budget |
| **Cost** | Free tiers only in MVP; cost recorded per decision; budgets enforced (CORE-14) |
| **Reliability** | Provider failover; degraded mode; health checks; no single provider is critical |
| **Security of the gateway itself** | API keys hashed at rest; secrets only via environment variables; no secrets in repo (pre-commit scan); request size limits; rate limits; dependencies pinned; CORS restricted to the Console origin; the judge LLM never receives tools; demo tools sandboxed |
| **Privacy** | Redaction in logs; hashed user refs; no training on user data; "no external model" mode possible (Tier 0/1 only) |
| **Observability** | Structured logs with request/session ids; metrics: decisions by type, tier escalation rate, latency, provider errors, cost |
| **Explainability** | Every decision has a human-readable reason and the exact span |
| **Accessibility** | Console keyboard-navigable, readable contrast, works at phone width |
| **Portability** | Docker image; config via env + YAML; SQLite → Postgres migration path |
| **Licensing / originality** | All code written during the sprint; third-party libraries/models/datasets listed with licences; avoid AGPL in the core |
| **Testing** | Unit tests per component; contract tests for adapters; integration tests per surface; evaluation as a regression suite in CI |

---

## 13. Technology stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| API / Proxy | FastAPI, httpx, Pydantic |
| Reference agent | LangGraph |
| Extraction | pypdf / pdfplumber, python-docx, BeautifulSoup, stdlib `email`; RapidOCR (P1) |
| Local classifiers | Open prompt-injection classifiers from Hugging Face (licence checked, e.g. ProtectAI DeBERTa v2, Apache-2.0) |
| AI judge / agent models | Free tiers: Groq, Gemini, OpenRouter free models, Mistral, NVIDIA (model names in config) |
| Storage | SQLite |
| Console | React + Vite + Tailwind (static build) |
| Hosting | Backend: Hugging Face Spaces (Docker). Console: Vercel / Netlify / Cloudflare Pages |
| CI | GitHub Actions: lint, tests, small eval subset |

---

## 14. Attack-type coverage matrix

| # | Attack type (PDF) | Primary checkpoint | Main signals | Channels tested |
|---|---|---|---|---|
| 1 | Instruction Override | Inbound | Tier 0/1/2 | user, web, PDF, email, DOCX, API |
| 2 | Role Change | Inbound | Tier 0/1/2 | user, web, email |
| 3 | Secret Extraction | Inbound + outbound scan | Tier 1/2 + canary/secret scan | user, web, PDF, email |
| 4 | Tool Abuse | Action guard | Allowed tools, task-fit, pinned fields | tool results, web, email |
| 5 | Credential Theft | Inbound + outbound scan | Tier 1/2 + credential patterns | email, web, API |
| 6 | Context Poisoning | Inbound (retrieved/stored content) | Tier 0/1/2 on retrieval | DB records, files, RAG docs |
| 7 | Multi-Step Jailbreak | Session risk | Accumulated risk | user (multi-turn), mixed |
| 8 | Encoded Instructions | Normaliser → detector | Decoding + Tier 0/1/2 | all text channels |
| 9 | Indirect Prompt Injection | Inbound on all non-user channels | Extraction + Tier 0/1/2 | web, PDF, DOCX, email, HTML, MD, code, API, OCR |

Only types that meet the recall target in the evaluation are claimed.

---

## 15. Grid claim rule (F/D self-declaration)

- **F:** count attack types with recall ≥ 85% **and** FPR ≤ 5% on the published evaluation. ≥7 → F3, ≥5 → F2, ≥2 → F1.
- **D:** **D2** if text channels meet targets. **D3** only if PDF/DOCX/HTML *and* images via OCR also meet the same targets.
- Supporting features demonstrated: observability (CORE-10, CON-2), fault tolerance (CORE-12), trainability (EVAL-4).
- The declared position, its evidence and the evaluation date go in the README, deck and Console scorecard.

---

## 16. Demo scenarios (Playground and video)

Each scenario runs with protection OFF then ON. Attack content is described here by category only; concrete test content lives in the evaluation corpus.

| # | Scenario | Attack type(s) | Channel | Expected OFF → ON |
|---|---|---|---|---|
| S1 | Summarise an uploaded report with hidden text | Indirect, Override | PDF | Agent obeys hidden text → span quarantined, summary correct |
| S2 | Triage an email asking the assistant to forward data | Credential Theft, Tool Abuse | Email | Canary sent to outbox → send blocked with reason |
| S3 | Research a web page that tries to reassign the assistant's role | Role Change, Indirect | HTML | Role change followed → neutralised |
| S4 | Look up a customer; retrieved record carries an instruction to query other customers | Context Poisoning, Tool Abuse | DB / RAG | Cross-customer query → pinned field enforced |
| S5 | Encoded instruction in a Markdown note | Encoded | Markdown | Decoded instruction followed → caught after normalisation |
| S6 | Attack spread across several turns | Multi-Step | User | Gradual hijack → session risk blocks |
| S7 | Request to reveal configuration/secrets | Secret Extraction | User | Leak → refused; outbound scan |
| S8 | Ordinary security article and code samples | Benign (hard) | Web, code | Works both ways; no false alarm |
| S9 | Unmodified agent through the proxy | Indirect via tool results | Proxy | Same protection with one setting changed |

**Video storyline (≈3:30):** problem in users' words (0:00–0:25) → S2 unprotected (0:25–0:55) → same with protection plus replay (0:55–1:40) → S1 and S8 (span removal, no false alarm) (1:40–2:20) → proxy one-line adoption (2:20–2:45) → scorecard and grid claim (2:45–3:15) → architecture and close (3:15–3:30).

---

## 17. Deployment and configuration

| Item | Plan |
|---|---|
| Backend | One Docker image on Hugging Face Spaces: FastAPI app serving `/v1`, `/proxy/v1`, `/demo`; engine + local classifiers + SQLite |
| Console | Static build on Vercel/Netlify/Cloudflare Pages; talks to backend over HTTPS with the public read-only key |
| Secrets | Provider keys as host secrets / `.env` locally; never committed; `.env.example` documents names only |
| Config | `config/models.yaml` (providers, models, failover order), `policies/*.yaml` |
| Cold start | Spaces may sleep: Console shows a "waking up" state; warm-up endpoint pinged before recording the video |
| Offline jobs | Evaluation and adversary loop run locally or in CI; results committed as reports |

---

## 18. Repository structure

```
agent-security-gateway/
├── packages/core/        # Core Engine
├── packages/sdk/         # Python SDK
├── services/gateway/     # FastAPI: API + proxy + demo endpoint
├── apps/console/         # React Security Console
├── agents/research_agent/# Reference agent + sandboxed tools + fixtures
├── eval/                 # corpus, runner, adversary loop, reports
├── policies/  config/    # YAML
├── docs/                 # architecture, evaluation report, grid justification
└── README.md             # quick start, claims, credits, licences
```

---

## 19. Submission package (definition of done)

| Item | Done when |
|---|---|
| Public GitHub repo | Opens logged-out; README has: one-line promise, demo link, video link, quick start (SDK + proxy), architecture diagram, evaluation results, F/D claim with evidence, limitations, credits and licences |
| Public demo link | Console Playground runs S1–S9 from a logged-out browser |
| Architecture document | Process flow, components, decisions, model usage, and how each claimed feature is backed by code and demo (`docs/ARCHITECTURE.md`) |
| Evaluation report | `docs/EVALUATION.md` + JSON, generated by EVAL-2, dated |
| Pitch deck (PDF) | 10–12 slides: problem (real quotes), who it's for, solution, architecture, live demo screenshots, metrics, F/D claim, responsible AI, business impact, roadmap |
| Demo video (2–4 min) | Public link, follows §16 storyline |
| Naming | Files and links named clearly (e.g. `AgentSecurityGateway_Deck.pdf`) |
| Final check | All links tested in an incognito window before pressing Submit on Unstop |

---

## 20. Timeline (today Sun 5 Oct → Sat 11 Oct)

| Day | Date | Milestone | Exit criteria |
|---|---|---|---|
| 1 | Sun 5 Oct | **Validate** A1–A6 (≈3 h); repo scaffold; reference agent + sandboxed tools; corpus v0; unprotected baseline | Attacks measurably succeed unprotected on a free model |
| 2 | Mon 6 Oct | CORE-1…CORE-8 (extraction, normalisation, tiers, labels, session, policy, neutraliser) | First recall/FPR numbers |
| 3 | Tue 7 Oct | CORE-9…CORE-15 (action guard, logger, router, fail-safe, DecisionModel, cost, modes) + SDK-1…SDK-5 | S1–S7 pass via SDK |
| 4 | Wed 8 Oct | API-1…API-10 + PRX-1…PRX-5 | S9 passes via proxy |
| 5 | Thu 9 Oct | Console CON-1…CON-5, CON-10; deploy backend + Console | Public link runs S1–S9 |
| 6 | Fri 10 Oct | EVAL full run + EVAL-4 if time; decide F/D claim; architecture doc, README, deck, video | All artefacts drafted |
| 7 | Sat 11 Oct | Buffer; polish; incognito link check; **submit by evening** | Submitted |

**Cut order if behind (first cut first):** EVAL-4 adversary loop → CORE-2b OCR → CON-9 approvals → CON-7/8 → SDK-6/7 → PRX-6 streaming → CON-6 cost panel. P0 items are never cut. If a P0 slips, lower the grid claim rather than overstate.

---

## 21. Jev slot (deferred, designed in)

- **Now:** `DecisionModel` interface (CORE-13) with a generative-free-LLM adapter. Policy key `decision_model: generative_free`.
- **Later:** add a `JevDecisionModel` adapter: 9 attack-type Nouls + "instruction aimed at an AI" Noul + severity Score per chunk; action task-fit Nouls; confidence-gated escalation. Switch with `decision_model: jev`. No engine changes.
- **Experiment plan (EVAL-6):** same corpus, same policy, three configurations: (a) free generative judge, (b) Jev, (c) both with disagreement → escalate. Compare recall/type, FPR, utility, p95 latency, cost per 1k tokens, and judge-steering robustness (doc 10, A7/A8).
- **Rules that still apply:** Jev is never the sole authority; pin `jev-1.13.0`; budget cap applies.

---

## 22. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Free-tier quotas/rate limits during eval or demo | High | High | Router failover across 5 providers; caching; smaller eval subsets; record video against warm cache |
| Free models don't call tools reliably | Medium | High | Validate A1 on Day 1; pick the best free tool-caller; keep tools few and simple |
| Local classifiers weak on indirect/encoded content | Medium | Medium | Normalisation first; Tier 2 judge; measure honestly |
| HF Spaces resources/cold start | Medium | Medium | Validate A4; small classifier; warm-up; fallback host (Render/Fly) |
| Proxy parsing differs across providers | Medium | Medium | Validate A5; support two providers first |
| Scope creep across five surfaces | High | High | P0 discipline; cut order; daily exit criteria |
| Over-claiming grid position | Medium | High | §15 rule; claims only from the evaluation report |
| Judge LLM steered by content | Medium | Medium | Rules decide; ensemble; judge gets no tools; adversary loop targets it |
| Dataset licence issues in a public repo | Low | Medium | Use permissive datasets or our own synthetic cases; list licences |
| Solo bandwidth / illness | Medium | High | Buffer day; video can be recorded Day 6 |

---

## 23. Open questions

| # | Question | Owner | Blocking? |
|---|---|---|---|
| Q1 | Final product name (repo, deck, video) | Sankalp | By Day 5 |
| Q2 | Free API keys placed in local `.env` (Groq, Gemini, OpenRouter, Mistral, NVIDIA) | Sankalp | **Yes, Day 1 morning** |
| Q3 | Hugging Face account for Spaces; Vercel/Netlify account for Console | Sankalp | By Day 5 |
| Q4 | Which free model is the reference agent's default (decided by A1) | Engineering | Day 1 |
| Q5 | Exact public datasets used (licence check) | Engineering | Day 1 |
| Q6 | GitHub repo name and visibility switch timing (public before submission) | Sankalp | Day 6 |
