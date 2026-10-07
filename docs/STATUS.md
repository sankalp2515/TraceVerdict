# Status

Updated: **Tue 7 Oct 2026 (Day 3 of 7)** · Deadline **Sat 11 Oct 2026, 11:59 PM IST** · Product name: **IntentSeal** · tagline “Keep AI agents inside the user’s intent” (D-032)
Tests: **148 passing** offline (`.venv/Scripts/python -m pytest -q`) · lint clean (`ruff check .`) · secret scan clean (`python scripts/secret_scan.py --all`).

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
| CORE-16 (P1) | 🟡 | Chunking + body limit; no span re-mapping across chunks |
| CORE-17 (P2) | 🟡 | Entity provenance only |

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
| API-12 (P2) | ❌ | |
| PRX-1…5 | ✅ | Unmodified OpenAI-SDK agent protected by `OPENAI_BASE_URL` alone (`examples/openai_agent`, test with the real `openai` client) |
| PRX-6 (P1) | 🟡 | Single-chunk streaming compatibility; no incremental upstream streaming |

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
| Docs | ✅ README, ARCHITECTURE.md, EVALUATION.md (generated), ENGINE.md, DECISIONS D-021…D-028 |
| Docker / hosting / Console UI | Owner (excluded from this pass) |
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

Open from before: DEF-013 (Groq rejects some malformed tool calls), DEF-015 (Console visual quality → owner).

## 5. What is left

The full, prioritised list lives in **`docs/BACKLOG.md`**. Summary:

1. **Owner:** product name (Q1); Console UI/UX; Docker + hosting + public links; deck and video; EVAL-4 adaptive round
   (generator choice per D-005/D-014; the memory/feedback backend is ready).
2. Optional engineering (P1/P2): PRX-6 incremental streaming; CORE-16 span re-mapping; API-12; EVAL-6 (Jev).
3. Before submission: rerun `eval/run_protected.sh` + `python -m intentseal_eval.summary` on the final commit; commit the reports.
