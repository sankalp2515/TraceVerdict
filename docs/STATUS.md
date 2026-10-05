# Status

Deadline: **Sat 11 Oct 2026, 11:59 PM IST**. Product name: `<PRODUCT_NAME>` (pending).

## Milestones

| # | Scope | State | QA note |
|---|---|---|---|
| M0 | Docs read; repo; config-driven providers; `asg providers check`; Validate A1–A6 | **Done (A6 deferred to M1)** | 12 router tests pass (failover, 429/retry-after, 401 key disable, 5xx circuit, timeout, zero keys, budget, cache, key loading, redaction). `providers check` run live: all active keys OK. Secret scan hook installed. A6 moved to M1 (D-010) |
| M1 | Reference agent, sandboxed tools, fixtures; promptfoo/garak harness; runner; baseline; A6 | **Mostly done** | Agent + target + benign suite (20/20 unprotected) + report. Unprotected baseline on 4 of 12 channels: 231 tests, ASR 4.3% (deterministic lower bound) on Nemotron. Remaining: 8 channels, garak, gpt-oss-120b headline baseline, A6 |
| M2 | Core Engine CORE-1…15 + CORE-2b OCR (P0) | **Code complete; measurement pending** | Extract (10), normalise (5), action guard (14), engine (44, written by owner with Codex, D-018) tests pass. Protected measurement blocked by DEF-007 |
| M3 | SDK-1…5; S1–S7 via SDK | **SDK written** | Guard, inspect, @tool, session, fail-open/closed; tests + scenarios pending |
| M4 | API-1…10, PRX-1…5; S9 via proxy | — | — |
| M5 | Console CON-1…5, 10 | — | — |
| M6 | Full eval, P1s, docs, grid claim, deck outline, video script | — | — |

## Defects

| ID | Sev | Description | State |
|---|---|---|---|
| DEF-001 | Med | Log-redaction filter broke `%d` log formatting (found in M0) | Fixed |
| DEF-002 | Med | Router throttles by requests/min only; Groq free tier is bound by tokens/min (8k) → 429s under load. Add `limits.tpm` | Open (M2) |
| DEF-003 | Low | Gemini `gemini-flash-latest` intermittent 5xx; Gemini 3.5 Flash ~25 s per call | Mitigated (not in role lists) |
| DEF-004 | High | Tier 1 classifiers: FPR 52% on hard-benign (A2) | Design change D-011 |
| DEF-005 | Med | Tier 1 latency on long text on 2 vCPU (A4) | Design change D-013 |
| DEF-006 | Med | On image OCR failure the extractor passed raw PNG bytes on as text | Fixed (no text + warning; engine holds) |
| DEF-007 | **High (env)** | Dev machine out of commit memory (page file 0.4 GB free): classifier/OCR allocations fail; protected runs cannot start | Open: owner to free memory |
| DEF-008 | Med | Report counted promptfoo assertion failures as errors | Fixed |

## Open questions for Sankalp
- Q1 product name (by Day 5). Q3 hosting accounts (by Day 5). Q6 repo name / public timing.
