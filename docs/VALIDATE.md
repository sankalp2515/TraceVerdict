# Validate report (M0) — risky assumptions A1–A6

> Date: 5 Oct 2026. Source: docs/09 §10. Raw results: `eval/validate/results/*.json` (scores only).
> Attack content was loaded from licensed public datasets by code and never printed or quoted.

## Summary

| # | Assumption | Result | Verdict | Consequence |
|---|---|---|---|---|
| A1 | Free models call tools reliably and are hijackable when unprotected | Benign tool tasks 100% on all 4 models. Real attack emails (LLMail-Inject) hijacked: gpt-oss-120b **50%** (n=10), Nemotron-3-Super **15%** (n=20), Gemini 3.1 Flash-Lite **11%** (n=18). Planted secret leaked 0–20% (direct extraction set) | **Pass** | Baseline gap is measurable. Agent default: gpt-oss-120b (Groq), fallbacks Gemini Flash-Lite, Nemotron (NVIDIA) |
| A2 | Local classifiers catch attacks with acceptable false alarms | ProtectAI DeBERTa v2: recall 67%, FPR 20%, **FPR 52% on hard-benign**. Prompt Guard 2 (Groq API): recall 40%, FPR 6% (n=131 labelled sample) | **Fail as decider** | Classifiers are escalation signals only; rules + AI judge + action guard decide (D-011) |
| A3 | Free quotas cover evaluation volume | Groq: 1,000 req/day and 8,000 tokens/min per model (Prompt Guard 2: 14,400/day). NVIDIA: 0 errors over ~150 calls. OpenRouter key on free tier. Gemini: no published headers | **Pass with conditions** | ≈2 full eval runs/day if escalation ≤40% with caching; router needs a tokens-per-minute throttle (DEF-002) |
| A4 | Free HF Spaces hardware suffices | Docker, 2 vCPU / 16 GB: 1.2 GB RAM, 8.7 s model load. Classifier p50: 30 words 132 ms, 150 words 581 ms, 400 words 1.5 s. int8 quantisation rejected (mean prob. shift 0.48) | **Pass (RAM), fail (latency on long text)** | Tier 1 runs only on short rule-flagged segments + content-hash cache (D-013) |
| A5 | Proxy can parse tool calls from multiple providers | 8 models / 4 providers: well-formed tool calls and full tool round trip | **Pass** | PRX-4 feasible on Groq, Gemini, NVIDIA, OpenRouter |
| A6 | Span-level neutralisation keeps the agent useful | Not run in M0 | **Open** | Runs in M1 through promptfoo-generated embedded cases + our utility scoring (D-010) |

## Details

### Providers and models (config verified)
- Keys present: Groq ×3, Gemini ×3, OpenRouter ×1, NVIDIA ×2, Mistral ×0 (auto-disabled), Jev disabled.
  One key per provider is active; others are emergency spares (D-004). groq#1 was rejected on first run,
  disabled automatically with an alias-only alert, and passed after the owner fixed it.
- Gemini 2.5 models return 404 "no longer available to new users" → Gemini 3.x. NVIDIA lists Kimi but
  does not serve it to our account → Nemotron-3-Super / gpt-oss-20b.

### A1 method
Minimal tool loop (web_fetch, read_file, read_email, query_db, write_file, send_message; all sandboxed).
Benign: 8 tool tasks with deterministic answers. Attacks: 20 emails sampled from LLMail-Inject Phase 1 rows
that fully succeeded in the challenge; success = agent sends mail to the dataset's target address. Secret
extraction: 10 Gandalf prompts against a fresh random canary password. Groq runs had rate-limit errors
(13 and 27 calls) from running two validations concurrently; Groq numbers have smaller n.

### A2 method
131 items: 66 attacks (deepset, neuralchemy by category, LLMail, Gandalf) and 65 benign (deepset,
neuralchemy, jackhhao, our 25 hard-benign). Recall varied by source: 100% on several direct sets, 47% on
LLMail emails, 13–20% on the multilingual deepset set. 22 Prompt Guard calls hit Groq's per-minute limit.

### What changed in the plan
D-010 (promptfoo + garak as attack generators), D-011 (classifiers advise, never decide), D-012 (agent
model order), D-013 (segment-level Tier 1 + cache). See docs/DECISIONS.md.
