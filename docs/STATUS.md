# Status

Deadline: **Sat 11 Oct 2026, 11:59 PM IST**. Product name: `<PRODUCT_NAME>` (pending).

## Milestones

| # | Scope | State | QA note |
|---|---|---|---|
| M0 | Docs read; repo; config-driven providers; `asg providers check`; Validate A1–A6 | **Done (A6 deferred to M1)** | 12 router tests pass (failover, 429/retry-after, 401 key disable, 5xx circuit, timeout, zero keys, budget, cache, key loading, redaction). `providers check` run live: all active keys OK. Secret scan hook installed. A6 moved to M1 (D-010) |
| M1 | Reference agent, sandboxed tools, fixtures; promptfoo/garak harness; runner; baseline; A6 | **Mostly done** | Unprotected baselines: broad (Nemotron) 231 tests ASR 4.3%; headline (gpt-oss-120b) 28 scored, ASR 25.0%. Benign utility 20/20. Remaining: 8 more channels, garak, A6 |
| M2 | Core Engine CORE-1…15 + CORE-2b OCR (P0) | **Done; measuring** | Engine 46 tests (Codex-authored + D-019 fix). Protected benign 20/20 (0 false alarms in 39 inspections); hard-benign FPR 1/25 = 4%; escalation ~8% on benign tasks; fast path p95 196 ms |
| M3 | SDK-1…5; S1–S7 via SDK | **SDK done** | Guard used by eval + demo; S1–S7 need scenario content (owner) |
| M4 | API-1…10, PRX-1…5; S9 via proxy | **Done** | 10 integration tests: auth/scopes, rate + size limits, CORS, all endpoints, proxy blocks external send + rewrites pinned field + inspects tool results, stream, upstream down → 503. OpenAPI at /docs. S9 needs scenario content |
| M5 | Console CON-1…5, 10 | **Done** | Checked in built-in browser: S8 OFF/ON identical (no false alarm), replay timeline, scorecard; phone width (no horizontal scroll) + dark theme. Fixed: picker width on phones, theme saved only on explicit choice, cold-start degraded decision (warm-up) |
| M6 | Full eval, P1s, docs, grid claim, deck outline, video script | — | — |

## Defects

| ID | Sev | Description | State |
|---|---|---|---|
| DEF-001 | Med | Log-redaction filter broke `%d` log formatting (found in M0) | Fixed |
| DEF-002 | Med | Router throttles by requests/min only; Groq free tier is bound by tokens/min (8k) → 429s under load | Fixed (tpm throttle, cooldown waiting, max_queue_s fail-over) |
| DEF-003 | Low | Gemini `gemini-flash-latest` intermittent 5xx; Gemini 3.5 Flash ~25 s per call | Mitigated (not in role lists) |
| DEF-004 | High | Tier 1 classifiers: FPR 52% on hard-benign (A2) | Design change D-011 |
| DEF-005 | Med | Tier 1 latency on long text on 2 vCPU (A4) | Design change D-013 |
| DEF-006 | Med | On image OCR failure the extractor passed raw PNG bytes on as text | Fixed (no text + warning; engine holds) |
| DEF-007 | High (env) | Dev machine out of commit memory | Resolved by owner |
| DEF-008 | Med | Report counted promptfoo assertion failures as errors | Fixed |
| DEF-009 | **High** | Plain-text attacks (no structural flag) skipped Tier 1/2 entirely | Fixed (D-019) + tests |
| DEF-010 | Med | Extractor flagged titles/metadata, code comments, HTML-only email text as non-visible → benign content neutralised | Fixed (D-020) |
| DEF-011 | Med | Judge unparseable/truncated replies (strict JSON mode rejected, reasoning ate token budget) → degraded holds | Fixed (no JSON mode, 1000 tokens, low reasoning effort) |
| DEF-012 | Low | Report excluded runs that errored after a verified harmful action | Fixed |
| DEF-013 | Low | Groq gpt-oss-120b occasionally rejects malformed tool calls (HTTP 400) → agent run errors (5 of 30 headline tests) | Open: report as errors; consider retry |

## Open questions for Sankalp
- **Demo scenarios S1–S7, S9**: attack content for eval/scenarios/*.yaml (owner/Codex; format in services/gateway/asg_gateway/demo.py)
- Q1 product name (by Day 5). Q3 hosting accounts (by Day 5). Q6 repo name / public timing.
