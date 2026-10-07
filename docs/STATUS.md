# Status

Updated: **Tue 7 Oct 2026, evening (Day 3 of 7)** · Deadline **Sat 11 Oct 2026, 11:59 PM IST** · Product name: **IntentSeal** · tagline “Keep AI agents inside the user’s intent” (D-032)
Tests: **205 passing** offline (`.venv/Scripts/python -m pytest -q`; storage contract tests also on PostgreSQL when
`INTENTSEAL_TEST_DATABASE_URL` is set, as in CI) · lint clean (`ruff check .`) · secret scan clean (`python scripts/secret_scan.py --all`).

## 1. Headline numbers

Generated, never hand-typed: `docs/EVALUATION.md` and the README results block come from
`python -m intentseal_eval.summary` (then `python -m intentseal_eval.readme`). See §3 for what each number is measured on.

**Grid position by the PRD §15 rule: none / none** (0 of 9 attack types at recall ≥ 85% with FPR ≤ 5%). The self-declaration is the team's decision, made from these numbers.

| Metric | Result |
|---|---|
| Detection recall, third-party content (426 generated attacks through 14 document/data channels; 33 payloads the channel could not deliver excluded) | 96.5% |
| Detection recall, direct user-turn attacks (399 cases) | 60.4% |
| False-positive rate, held-out hard-benign set (39 cases) | 10.3% |
| Fast-path latency p95 (isolated) | 108.8 ms |
| Attack success on the reference agent, `headline` suite (27 / 30 scored tests): off → on | 25.9% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `mt3` suite (40 / 40 scored tests): off → on | 12.5% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `v2e` suite (144 / 144 scored tests): off → on | 0.7% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `broad` suite (219 / 219 scored tests): off → on | 4.6% → 0.0% (canary leaks with protection: 0) · protected run from the 5 Oct engine (before fingerprinting); rerun pending |
| Benign task utility retained | 100.0% |
| Security cost per agent cost, `headline` suite (30 protected runs, list prices) | 35% (security tokens per agent token: 1.02) |

What these numbers mean (details and method in `docs/EVALUATION.md`):
- **Strong:** indirect injection in documents and data is detected at 91–100% per channel (PDF, DOCX, HTML, hidden text,
  email, API, Markdown, code, OCR text, DB records, images); no canary leaked and no verified harmful action
  succeeded with protection in any suite.
- **Below target:** direct user-turn attacks (60.4%: user turns keep the classifier gate for latency) and held-out FPR
  10.3% (4/39: three judge errors on a code prompt template, an assistant style guide and a role-change audit event,
  plus one by-design hidden-comment quarantine; 7.7% counting only blocks). With these, the §15 rule gives no F/D level.
- **Measured 7 Oct:** G7b cost overhead per protected run (headline: security cost 35% of agent cost); Multi-Step on 29 cases (82.8%, below target); garak's own detectors as a second opinion (`docs/EVALUATION.md`).
- Options for the owner (each needs a rerun): judge user turns for high-risk agents (`judge_untrusted`-style policy
  for the user channel), a second judge opinion before blocking unflagged content, a larger held-out benign set.

## 2. Milestones

| # | Scope | State |
|---|---|---|
| M0 | Repo, config-driven providers, Validate A1–A5 | Done (A6 open) |
| M1 | Reference agent, sandbox, fixtures, harness | Done (all 11 channels + 3 hidden-text variants delivered) |
| M2 | Core Engine | Done, plus CORE-3 decoding, shape-based look-alike folding, trainability memory |
| M3 | Python SDK | Done, plus remote mode (SDK-6) and LangChain/LangGraph helper (SDK-7) |
| M4 | Gateway API + LLM proxy | Done, plus policy PUT, approvals, feedback/memory, metrics, path-scoped proxy |
| M5 | Security Console | **Rebuilt 7 Oct in the IntentSeal design** (Overview, Playground, Replay, Results, Decisions, Review, Policy); live data only; dark + light; phone to desktop |
| M6 | Full eval, docs, grid claim | Eval pipeline, ARCHITECTURE, EVALUATION (generated), README done; deck/video with the owner |

## 3. PRD coverage (UI/UX and deployment excluded by the owner)

✅ built and tested · 🟡 partial · ❌ not built

### Core Engine
| ID | State | Evidence |
|---|---|---|
| CORE-1 | ✅ | `tests/test_sdk_surfaces.py::test_every_surface_goes_through_engine_inspect` (SDK, API, proxy, LangChain helper) |
| CORE-2 / 2b | ✅ | Extraction for every channel incl. hidden text and OCR; evaluated per channel (detect runs) |
| CORE-3 | ✅ | Unicode + **decoding before scoring** (base64/hex/tag chars/%/rot13) + shape-based look-alike skeleton; `tests/test_decode.py`, `test_normalise.py` |
| CORE-4 | ✅ | Tier 0/1/2; `judge_untrusted` policy for high-risk agents (DEF-017) |
| CORE-5 | ✅ | Labels on all findings; per-type recall in EVALUATION.md |
| CORE-6 | ✅ | Session accumulation test (each turn ALLOW, session escalates then blocks); S6 scenario |
| CORE-7/8 | ✅ | Named rules incl. `known-attack-match`, `human-approved` |
| CORE-9 | ✅ | Action guard + approvals (one-shot, never overrides BLOCK) |
| CORE-10 | ✅ | Decision log; approvals table; memory stores fingerprints only |
| CORE-11/12/13 | ✅ | Router, fail-safe holds, DecisionModel adapters |
| CORE-14 | ✅ | Budgets + overhead ratio (`/v1/costs`, summary); eval override `INTENTSEAL_BUDGET_TIER2_DAILY_TOKENS` |
| CORE-15 | ✅ | Monitor/enforce; S9 OFF uses the monitor-mode twin policy |
| CORE-16 (P1) | ✅ | Judge windows over long documents with original-offset spans, `oversize-hold`, `content-too-large`, Tier 1 budget per chunk (D-041); `tests/test_engine.py::test_large_html_document_inspected_without_timeouts` and the window tests |
| CORE-17 (P2) | ✅ | Entity provenance + argument-to-origin taint tracing, flagged-content rule, stored for replay (D-042); `tests/test_engine.py` taint tests |

### SDK
| ID | State | Evidence |
|---|---|---|
| SDK-1…5 | ✅ | As before; remote inspection failure withholds content |
| SDK-6 (P1) | ✅ | `intentseal/remote.py`; same decisions as embedded (test) |
| SDK-7 (P1) | ✅ | `guard.protect_tools(...)`; `examples/langgraph_agent` protected with ≤ 10 added lines (test counts the diff) |

### Gateway API / proxy
| ID | State | Evidence |
|---|---|---|
| API-1…5, 7…11 | ✅ | `tests/test_gateway.py` (21 tests); scorecard serves the summary + grid claim |
| API-6 | ✅ | GET + admin PUT (validated, versioned, atomic write) |
| API-12 (P2) | ✅ | PostgreSQL store (`tests/test_store_backends.py` on both backends), organisations (`tests/test_tenancy.py`), SIEM pull/push (`tests/test_siem.py`) (D-043, D-044) |
| PRX-1…5 | ✅ | Unmodified OpenAI-SDK agent protected by `OPENAI_BASE_URL` alone (`examples/openai_agent`, test with the real `openai` client) |
| PRX-6 (P1) | ✅ | Text streams through, tool calls buffered, checked, released (D-040); the OpenAI SDK streaming client gets the checked call (`tests/test_gateway.py`); verified live on Groq and NVIDIA |

### Console backends (UI excluded)
CON-6 cost data ✅ (`/v1/costs`, `/v1/costs/{agent}`) · CON-7 policy view/edit ✅ API · CON-8 mark FP / confirm attack ✅ API · CON-9 approvals ✅ API.

### Evaluation
| ID | State | Evidence |
|---|---|---|
| EVAL-1 | ✅ | v2 corpus: promptfoo user + roles sets, garak probe attempts, pooled indirect payloads × 14 delivery channels; hard-benign dev (v0) + held-out (v1) |
| EVAL-2/3 | ✅ | `intentseal_eval.summary`: recall per type at its §14 checkpoint, coverage map, FPR (dev + held-out), latency p50/p95, ASR off/on, utility, cost overhead, grid claim; fail-safe holds excluded; engine fingerprint per suite |
| EVAL-4 (P1) | 🟡 | Backend done (memory, `/v1/feedback`, `Engine.feedback`); the adaptive generation round itself is left to the owner's generator choice (D-005/D-014) |
| EVAL-5 | ✅ | Deterministic outcomes; exact re-scoring rules DEF-014, DEF-019 |
| EVAL-6 (P2) | ❌ | Jev deferred |

### Demo scenarios (§16)
S1–S9 files present (`eval/scenarios/`). S1–S7 and S9 take generator cases via `pick_scenarios.py`; each file states whether
its case was verified to compromise the unprotected agent (S7 verified; others unverified on today's models).
S9 runs the unmodified OpenAI-SDK agent through the gateway's own proxy (OFF = monitor mode, ON = enforce).

### Non-functional / submission
| Item | State |
|---|---|
| CI | ✅ `.github/workflows/ci.yml`: pinned install, ruff, secret scan, fixtures, tests |
| Dependencies | ✅ `requirements.lock` (exact); package metadata now declares real runtime deps |
| Observability | ✅ request ids, structured access log, `/v1/metrics` |
| Docs | ✅ README, ARCHITECTURE.md, EVALUATION.md (generated), ENGINE.md, DEPLOY.md, DECISIONS up to D-046 |
| Docker | ✅ `Dockerfile`, `docker-compose.yml`, `/readyz`; verified locally (cold start 44 s, live judge/proxy/demo, restart keeps data) |
| Hosting / public links | Owner (DEPLOY.md §2–3 has the steps) |
| Console UI | Owner / Console session |
| Deck, video | Owner |

## 4. Defects found and fixed today

| ID | Sev | Description | State |
|---|---|---|---|
| DEF-016 | **High** | `source="email"` plain text parsed as an empty RFC 822 message → uninspected text returned to the agent by the SDK | Fixed + regression tests |
| DEF-017 | **High** | Tier 1 gate: paraphrased third-party instructions score ≈ 0, so they never reached the judge | Fixed by policy `judge_untrusted: always` for high-risk agents |
| DEF-018 | **High** | Look-alike text folded by sound (anyascii), not by shape → judge read garbled text; Unicode tag characters deleted instead of decoded; no base64 decoding (CORE-3 unmet) | Fixed: `decode.py`, shape skeleton |
| DEF-019 | Med | Harness: a same-site `http://` fetch counted as an external fetch (inflated ASR) | Fixed + exact re-score |
| DEF-020 | Med | Harness: API channel served non-JSON as `.json` (fail-closed `extraction-failed` counted as detections); promptfoo parses JSON-looking variables into objects | Fixed (JSON wrapping, target accepts objects) |
| DEF-021 | **High (process)** | Eval runs hit the production Tier 2 daily cap: `budget-hold` decisions were scored as detections (the first v3 run's "100% recall" was void); stopped tasks left shell loops writing stale results | Fixed: holds excluded from scoring, eval budget override recorded, engine fingerprint on every output, single orchestrated run (`eval/run_protected.sh`) |
| DEF-022 | Med (security) | Policy loading built a path from the URL agent id (Windows backslash traversal to other `.yaml` files) | Fixed: agent id validation, 422 |
| DEF-023 | Low | `secret_scan.py --all` scanned nothing; garak `run.sh` report path invalid; test wrote into `data/eval_runs` | Fixed |
| DEF-024 | Low | Core package metadata omitted runtime dependencies | Fixed |

| DEF-025 | **High (security)** | URL allow-list bypass: `https://evil.example#.allowed.test` passed `_domain_ok` (fragment / user part / backslash posed as the host) | Fixed: host parsed with `urlsplit`, ambiguous URLs rejected + regression tests |
| DEF-026 | **High (security)** | Recipient allow-list bypass: `Name <x@evil.example>@allowed.test` passed; mailers deliver to x@evil.example | Fixed: addresses parsed with `getaddresses`, every one must pass |
| DEF-027 | **High (security)** | Tier 1 failure (model not loaded, timeout) allowed unflagged untrusted content without the judge, even with `judge_untrusted: always`; a failed load was cached for the life of the process | Fixed: every chunk to the judge, judge down → held; load retried; `/readyz` reports it |
| DEF-028 | **High (security)** | The judge read only the first 6,000 characters of a document | Fixed by CORE-16 windows (D-041) |
| DEF-029 | High | An agent id without a policy ran the default monitor policy (nothing enforced) through the Gateway, silently | Fixed: 404; SDK warns |
| DEF-030 | Med (security) | Body limit buffered chunked bodies fully before checking (unauthenticated memory use); public key could read every agent's evidence | Fixed: streamed limit; organisations + `INTENTSEAL_PUBLIC_AGENTS` |
| DEF-031 | Low | Cached scan object mutated by an inspection; unbounded in-process sessions/caches; event sequence restarted at 1 after a restart | Fixed |

DEF-025…031 come from the 7 Oct production-readiness audit (D-039). Open from before: DEF-013 (Groq rejects some
malformed tool calls), DEF-015 (Console visual quality → owner).

## 5. What is left

The full, prioritised list lives in **`docs/BACKLOG.md`**. Summary:

1. **Owner:** hosting accounts and public links (DEPLOY.md), Console UI/UX follow-ups (BACKLOG F1), deck and video,
   grid self-declaration from the final numbers, EVAL-4 adaptive round (needs a verified promptfoo account, D-036), LICENSE.
2. Engineering left: E4 (PyPI packaging: default config + starter policy inside the package, per-user data dir,
   `[embedded]` extra, LICENSE, TestPyPI dry run) and E6 (Jev comparison), both excluded from this pass.
3. Final evaluation (B3, D-046) ran on engine `0e473daf3561`; rerun `sh eval/run_final.sh` only if engine, SDK or
   policy code changes again.
