# Decisions log

Product name: **`<PRODUCT_NAME>`** placeholder until Q1 is decided. Code namespace `asg` ("Agent Security
Gateway", descriptive working name) is easy to rename.

| # | Date | Decision | Why | By |
|---|---|---|---|---|
| D-001 | 5 Oct | Free tiers and local open models only; Jev stays a disabled adapter slot | Budget; PRD §21 | Sankalp |
| D-002 | 5 Oct | Hosting deferred; keep Docker + static Console + env config deployable | Accounts later | Sankalp |
| D-003 | 5 Oct | Providers/models live in `config/providers.yaml` and `config/models.yaml`; nothing provider-specific in logic | Free lineups change (seen on day 1: Gemini 2.5 closed to new users) | Kickoff §3 |
| D-004 | 5 Oct | **One key per provider is used; other keys are emergency spares** used only if the active key is rejected (401/403/revoked). A 429 cools the provider down (honouring retry-after) and the router fails over to the next *provider*, never to another account's key | Spare keys come from separate accounts; using them to multiply rate limits would breach provider terms | Sankalp + Eng |
| D-005 | 5 Oct | Claude does not author attack test text. Attack cases come from licensed open-source red-team tools / public research datasets, owner-written cases (`eval/corpus/AUTHORING.md`), the variant generator and the adversary loop. Engineering handles case text only through code | A safety filter stops Claude writing payload text; docs stay at category level | Sankalp + Eng |
| D-006 | 5 Oct | **Variant generator** added to EVAL: places seed attacks into all 11 input sources, applies obfuscations and splits across turns/chunks; evaluation reported as a 9 types × 11 sources coverage map | PDF requires all 9 types across all listed sources; makes D3 measurable | Sankalp (accepted PM rec.) |
| D-007 | 5 Oct | **Target D3, fallback D2.** Images via OCR (CORE-2b) promoted **P1 → P0** and removed from the cut order | PDF lists images explicitly; D3 needs heterogeneous multimodal input | Sankalp (accepted PM rec.) |
| D-008 | 5 Oct | Adversary loop (EVAL-4) moved from first-cut to second-to-last in the cut order | Static-only numbers are discounted by experts; covers trainability + agentic criterion | Sankalp (accepted PM rec.) |
| D-009 | 5 Oct | Gemini 2.5 models unavailable to new users → use Gemini 3.x / `-latest` aliases; Kimi on NVIDIA listed but not served | Live probe (docs/VALIDATE.md) | Eng |
| D-010 | 5 Oct | **promptfoo (MIT) and garak (Apache-2.0) generate attack variants** (embedding in documents, encodings, languages, multi-turn), replacing a custom variant generator. We configure, run and score them; coverage map 9 types × 11 sources stays | Claude is blocked from writing code that embeds attacks; established tools are more credible to judges | Sankalp |
| D-011 | 5 Oct | Tier 1 classifiers are **escalation signals, never deciders**. Final decisions come from rules + AI judge + action guard via the policy engine | A2: ProtectAI FPR 52% on hard-benign; Prompt Guard 2 recall 40% | Eng |
| D-012 | 5 Oct | Agent role order: Groq gpt-oss-120b → Gemini 3.1 Flash-Lite → NVIDIA Nemotron-3-Super. Judge: gpt-oss-20b (Groq) → Flash-Lite → gpt-oss-20b (NVIDIA) | A1/A5 results; spread load across providers | Eng |
| D-013 | 5 Oct | Fast path: Tier 0 rules on all content; Tier 1 only on short rule-flagged segments; scans cached by content hash; no int8 quantisation | A4: 2-vCPU latency 0.6–1.5 s on 150–400 words; int8 broke accuracy | Eng |

**Revised cut order (PRD §20, supersedes):** CON-9 approvals → CON-7/8 → SDK-6/7 → PRX-6 streaming →
CON-6 cost panel → EVAL-4 adversary loop. P0 (now including CORE-2b OCR) is never cut.
