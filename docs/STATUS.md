# Status

Updated: **Sun 5 Oct 2026, night (end of Day 1 of 7)** · Deadline **Sat 11 Oct 2026, 11:59 PM IST** · Product name: `[Product Name]` (pending, Q1)
Tests: **110 passing** (`.venv/Scripts/python -m pytest -q`).

## 1. Headline numbers (from `eval/reports/`; measured, nothing claimed yet)

| Metric | Result | PRD target | Notes |
|---|---|---|---|
| Attack success, **broad** suite (231 tests, Nemotron agent, 4 channels) | **4.3% → 0.0%** (10 → 0) | ≥ 80% relative reduction (G1) | Deterministic lower bound; small unprotected base rate |
| Attack success, **headline** suite (30 tests, gpt-oss-120b agent) | **25.0%** unprotected (7/28) · protected **pending** | G1 | Protected run 6 Oct (Groq 200K tokens/day cap) |
| Benign task utility, protected | **20/20 (100%)** | ≥ 90% (G3b) | All 11 channel types |
| False alarms, hard-benign set | **1/25 (4%)** | ≤ 5% (G3) | Remaining one is a real judge call on API-key-handling code |
| False alarms during benign tasks | **0 / 39 inspections** | — | |
| Fast-path latency p95 | **196 ms** | ≤ 300 ms (G7) | Local CPU; judge path ~1–2.5 s |
| Escalation to AI judge (benign) | **~8%** | low (cost) | |
| Canary leaks with protection | **0** | 0 (G2) | |
| Recall per attack type | **not yet computed** | ≥ 85% on ≥ 7 types (G5) | Needed for the F-axis claim (M6) |
| Adaptive ASR | not yet | reported (G6) | Adversary loop (EVAL-4) |

## 2. Milestones

| # | Scope | State | QA note |
|---|---|---|---|
| M0 | Repo, config-driven providers, `providers check`, Validate A1–A6 | **Done** (A6 open) | docs/VALIDATE.md |
| M1 | Reference agent, sandbox, fixtures, harness, baseline | **Mostly done** | Remaining: 8 more channels, garak run, A6 |
| M2 | Core Engine | **Done** | Engine authored with Codex (D-018) + QA fixes D-019/020 |
| M3 | Python SDK | **Done** | S1–S7 need scenario content |
| M4 | Gateway API + LLM proxy | **Done** | S9 needs a scenario + a real unmodified OpenAI-SDK client test |
| M5 | Security Console | **Functional only** | Works end to end, but **not investor-grade UI** (see §5) |
| M6 | Full eval, docs, grid claim, deck, video | **Not started** | |

## 3. PRD coverage, requirement by requirement

✅ built and tested · 🟡 partial · ❌ not built · (P1/P2 = lower priority by PRD)

### Core Engine (§8.1)
| ID | State | Evidence / gap |
|---|---|---|
| CORE-1 single entry point | ✅ | `Engine.inspect/check_action`; SDK, API, proxy, demo all use it |
| CORE-2 extraction (text, MD, HTML, PDF, DOCX, email, JSON, code) | ✅ | 10 tests; hidden content surfaced and flagged |
| CORE-2b images via OCR (P0 per D-007) | 🟡 | Works (RapidOCR); **not yet evaluated** on image-channel attacks |
| CORE-3 normalisation | ✅ | Library-first (ftfy, confusable-homoglyphs, anyascii) |
| CORE-4 tiered detection | ✅ | Tier 0 structural, Tier 1 on all content (D-019), Tier 2 judge |
| CORE-5 attack-type labels | 🟡 | Labels on every finding; **per-type recall not yet measured** |
| CORE-6 session risk with decay | 🟡 | Implemented; **multi-step scenario not yet demonstrated** |
| CORE-7 deterministic policy engine | ✅ | Named rules (docs/ENGINE.md), 46 tests |
| CORE-8 span neutraliser | ✅ | Quarantine + untrusted-data markers |
| CORE-9 action guard | ✅ | 14 tests: allow-lists, pinned fields, outbound secrets, provenance, session risk |
| CORE-10 decision logger | ✅ | Redacted previews, hashed user refs |
| CORE-11 LLM router | ✅ | 16 tests: failover, 429, 401, circuit, budgets, tokens/min |
| CORE-12 fail-safe | ✅ | Degraded holds verified live |
| CORE-13 DecisionModel + Jev slot | ✅ | `generative_free`, `jev` (disabled), `static` |
| CORE-14 cost controls | 🟡 | Per-decision tokens/cost, cache, budgets ✅; **overhead metric (CC7) not reported** |
| CORE-15 monitor/enforce | ✅ | Tested |
| CORE-16 input limits/chunking (P1) | 🟡 | Chunking ✅, API body limit ✅ |
| CORE-17 taint tracking (P2) | 🟡 | Simple provenance (entities) in session |

### SDK (§8.2)
| ID | State | Evidence / gap |
|---|---|---|
| SDK-1…5 | ✅ | Guard, inspect, `@guard.tool`, session, fail-open/closed |
| SDK-6 remote mode (P1) | ❌ | |
| SDK-7 LangGraph helper, ≤10-line adoption proof (P1) | ❌ | G8 needs this or the proxy proof |

### Gateway API (§8.3)
| ID | State | Evidence / gap |
|---|---|---|
| API-1…5, 7…10 | ✅ | 10 integration tests; OpenAPI at `/docs` |
| API-6 policy read | ✅ | PUT (admin, P1) ❌ |
| API-11 costs (P1) | ✅ | `/v1/costs` |
| API-12 (P2) | ❌ | |

### LLM Proxy (§8.4)
| ID | State | Evidence / gap |
|---|---|---|
| PRX-1…5 | ✅ tests / 🟡 demo | **Not yet shown with an unmodified real agent** (S9) |
| PRX-6 streaming (P1) | 🟡 | Single-chunk compatibility only |

### Security Console (§8.5)
| ID | State | Evidence / gap |
|---|---|---|
| CON-1 Playground | 🟡 | Works; only benign scenarios installed |
| CON-2 replay | ✅ | |
| CON-3 scorecard | 🟡 | ASR off/on by type and channel; **missing FPR, utility, latency, cost, static vs adaptive, grid claim** |
| CON-4 decisions feed | ✅ | |
| CON-5 status banner | ✅ | |
| CON-10 responsive / accessible / themes | 🟡 | Checked at phone width + dark; **visual quality not investor-grade** |
| CON-6…9 (P1) | ❌ | Cost panel, policy view, false-positive marking, approvals inbox |

### Reference agent (§8.6)
REF-1…4 ✅

### Evaluation (§8.7)
| ID | State | Evidence / gap |
|---|---|---|
| EVAL-1 corpus | 🟡 | promptfoo/garak + our benign sets (D-014); **8 of 12 channels not yet run; garak not yet run** |
| EVAL-2 runner | 🟡 | ASR, utility ✅; **recall/type, latency p50/p95, cost not in report** |
| EVAL-3 report | ✅ | Markdown + JSON, dated, commit-stamped |
| EVAL-4 adversary loop (P1) | ❌ | |
| EVAL-5 deterministic success | ✅ | Executed-call rule (DEF-014) |
| EVAL-6 Jev comparison (P2) | ❌ | Deferred by decision |

### Demo scenarios (§16)
S8 ✅ (benign, verified OFF/ON in the Console) · **S1–S7, S9 ❌ need content from owner (Codex)**

### Non-functional (§12) and submission (§19)
| Item | State |
|---|---|
| Docker image / deployability | ❌ Dockerfile not written yet |
| CI (lint, tests, small eval subset) | ❌ |
| Secrets: env-only, pre-commit scan, redaction, hashed API keys | ✅ |
| CORS, rate limits, size limits, judge without tools | ✅ |
| Dependencies pinned | 🟡 ranges in pyproject; no lock file |
| README, docs/ARCHITECTURE.md, docs/EVALUATION.md, grid claim | ❌ (M6) |
| Deck outline, video script | ❌ (M6) |
| Hosting + public links | ❌ deferred (owner accounts) |

## 4. What is left, in order

1. **Owner:** S1–S7, S9 scenario files · product name · UI/UX direction (§5).
2. Protected headline run (6 Oct) · remaining 8 channels · garak · A6 utility check.
3. **Detection recall per attack type** (F-axis) + latency and cost in the report + scorecard fields.
4. Dockerfile + CI + dependency lock.
5. S9 proof: an unmodified OpenAI-SDK agent through the proxy (G8).
6. EVAL-4 adversary loop (P1).
7. README, ARCHITECTURE.md, EVALUATION.md, grid claim, deck outline, video script.

## 5. UI/UX

The Console is functional but visually basic. This is a lifecycle miss: the design stage stopped at low-fidelity
wireframes (doc 09 §8) and went straight to code. Owner leads UI/UX (Codex / Lovable, or Claude Code with design
skills). Engineering supplies `docs/UI_BRIEF.md` (product, users, screens, states, data and API contract) and keeps
the Gateway API stable so any front end can plug in.

## 6. Defects

| ID | Sev | Description | State |
|---|---|---|---|
| DEF-001 | Med | Log-redaction filter broke `%d` formatting | Fixed |
| DEF-002 | Med | No tokens/min throttle (Groq 8K TPM) | Fixed |
| DEF-003 | Low | Gemini intermittent 503 / slow | Mitigated (judge order) |
| DEF-004 | High | Tier 1 classifier FPR 52% on hard-benign | Mitigated: judge clears it (FPR now 4%) |
| DEF-005 | Med | Classifier latency on long text | Mitigated: chunking + cache (p95 196 ms) |
| DEF-006 | Med | Raw image bytes passed as text on OCR failure | Fixed |
| DEF-007 | High (env) | Dev machine out of memory | Resolved by owner |
| DEF-008 | Med | Report counted assertion failures as errors | Fixed |
| DEF-009 | **High** | Plain-text attacks skipped Tier 1/2 | Fixed (D-019) |
| DEF-010 | Med | Benign metadata/comments flagged non-visible | Fixed (D-020) |
| DEF-011 | Med | Judge replies truncated/unparseable | Fixed |
| DEF-012 | Low | Errored runs with verified harm excluded | Fixed |
| DEF-013 | Low | Groq rejects some malformed tool calls (5/30 headline runs errored) | Open |
| DEF-014 | Med | Blocked calls counted as harm | Fixed (exact re-score) |
| DEF-015 | Med | Console visual quality below investor bar | Open → owner (UI brief) |

## 7. Open questions for Sankalp
- **Q1 product name** (by 9 Oct) · **scenarios S1–S7, S9** (now) · **UI/UX route** (now) · Q3 hosting accounts (by 9 Oct) · Q6 repo name / public timing (10 Oct)
