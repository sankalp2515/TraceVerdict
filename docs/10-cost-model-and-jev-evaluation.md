# 10 — Cost Model & Jev (TypeSafe System One) Evaluation

> Date: 4 Oct 2026. Sources read in full: TypeSafe launch post, typesafe.ai homepage, `awesome-jev-use-cases` README (all 1,167 lines), and official docs pages: introduction, models, Jev 1.13 jaggedness, LLM guardrails cookbook, confidence, legal, `llms.txt` index. OpenRouter listing confirmed via search.
> Vendor numbers are marked as such. Community numbers are unverified unless stated.

---

## Part A — Will security double the cost of the agents we protect?

### Short answer
**Only if it's designed naively.** If every piece of content and every tool call went to a second, equally expensive LLM, input-token cost would roughly double. Our design avoids that by construction.

### Why our design doesn't double cost

| Design choice | Effect on cost |
|---|---|
| **Scan content once, not every turn.** A document is inspected when it enters, then cached by content hash. The agent may re-read it in 10 turns; we pay once. | Agents re-send history every turn; we don't |
| **Tier 0 rules and Tier 1 local classifiers are free.** They run on our own CPU, with no per-token fee. | Most content stops here |
| **Tier 2 (AI judge) runs only on suspicious content**, and only on the suspicious spans, not the whole document. | A small fraction of tokens reaches a paid or rate-limited model |
| **Tool-call checks are tiny** (a tool name plus a few arguments, a few hundred tokens), and most are decided by rules (allowed tools, pinned fields, secret patterns). | Negligible |
| **The proxy adds no model call of its own.** It forwards the agent's existing call; inspection uses the same tiers. | No duplicate generation |
| **Our outputs are decisions, not text.** We never pay for generated prose. | Output tokens (usually the expensive kind) avoided |

### Cost formula (per protected agent, per period)

```
security_cost ≈ (new_untrusted_tokens × escalation_rate × judge_price)
              + (tool_calls × escalation_rate_actions × tokens_per_check × judge_price)
              + fixed hosting
```

where *escalation_rate* = the share of content that the free tiers can't settle (to be measured in Validate; a typical target is 2–10%).

### Illustration (assumed prices; real numbers come from our evaluation)

A research agent reads a 10,000-token PDF.

| | Tokens | Price assumption | Cost |
|---|---|---|---|
| Agent reads it with a mid-tier model | 10,000 in | $0.50–$3.00 per M input | $0.005–$0.030 |
| Our Tier 0 + Tier 1 | 10,000 | local | $0.00 |
| Our Tier 2 with a **generative** judge, escalated 10% of the time on 2,000 suspicious tokens | 200 expected | $0.50 per M | $0.0001 |
| Our Tier 2 with **Jev** on the **whole** document (not just suspicious spans) | 10,000 + ~500 question tokens | $0.042 per M (vendor list price) | $0.00044 |

Even the "scan everything with Jev" option is **about 1–9% of the agent's own input cost** in this example, not 100%. Final claims will be measured, not asserted.

### Cost controls and tracking (new product requirements)

The research didn't surface cost as a voiced pain, but the brief requires "minimal disruption", and an expensive guard gets switched off just like a noisy one. So cost is a design constraint:

| # | Control | What it does |
|---|---|---|
| CC1 | **Per-decision cost record** | Every logged decision stores tier used, model, input tokens and estimated cost |
| CC2 | **Content-hash cache** | The same content is never judged twice |
| CC3 | **Budgets** | Per-agent and per-day token/cost caps |
| CC4 | **Safe behaviour at the cap** | When a budget is hit: rules and local classifiers continue; high-risk content is held or blocked, never passed silently; the decision is marked `budget_degraded` |
| CC5 | **Quota-aware router** | Tracks each free provider's remaining quota and fails over before it's exhausted |
| CC6 | **Cost panel in the Console** | Spend per agent, per tier, per day; cost per 1,000 inspected tokens; share escalated to Tier 2 |
| CC7 | **Security overhead metric** | Security cost ÷ the agent's own model cost, reported on the scorecard |

---

## Part B — Jev: what it actually is

**Vendor:** TypeSafe AI (founder previously worked on the research behind ChatGPT at OpenAI, per the launch post). Launched 15 Sep 2026; waitlist removed 27 Sep 2026. Current model `jev-1.13.0`.

**Core idea:** a "System One" model that **does not generate text**. You send a `state` (text or JSON) and a set of typed questions; it returns typed answers with probabilities, all questions evaluated **in parallel in one request**.

| Question type | Returns | Example use for us |
|---|---|---|
| **Noul** | probability (0–1) that a statement is true | "Does this text contain an instruction aimed at an AI assistant?" |
| **Choice** | chosen option + probability per option + confidence | "Which of the 9 attack types best describes this span?" |
| **Score** | level on an ordered rubric + probabilities + confidence | "How harmful would following this be?" |

**Official facts (models page, read 4 Oct):**

| Item | Value |
|---|---|
| Price | $0.042 per million input tokens; **output tokens free** |
| Rate limits | 100K tokens/s, 80 requests/s, **"adjusting dynamically… can change without notice"** (the community repo quotes older, higher numbers; the official page wins) |
| Context | 64k tokens per request; **32k for state + the longest question** |
| Input | **Text only.** Images, audio, video must be converted to text first |
| Languages | English best; others "handled but not equally well" |
| Training on customer data | No. Zero data retention only for enterprise |
| Access | TypeSafe API (`POST /v1/systemone`), Python and JS SDKs; **also listed on OpenRouter** at the same price |
| Free tier | **None found.** A Vercel free window ended 25 Sep. It's paid but very cheap |

### Claims vs. evidence (research-engineer view)

| Claim | Evidence quality | Our reading |
|---|---|---|
| 70–500 ms per call | Vendor; easy to verify; many community demos agree (e.g. ~400 ms per decision reported in `reflex`) | **Credible** |
| $0.042/M, output free | Official price list; vendor admits it can't prove it isn't subsidised | **Credible today; may change** |
| "Can't hallucinate" / no type errors | True only in the narrow sense that answers always match the schema. It **can still be wrong.** | **Reframe as "never malformed"** |
| 193.6× faster, 444.6× cheaper | Vendor's own workflow evals; reference answers are the average of two frontier LLMs; vendor says these are "on the higher end" | **Treat as upper bound** |
| Calibrated confidence | Vendor claim; one independent audit repo exists (`jev-calibration-audit`), not reviewed | **Must measure on our data** |
| Good as a guardrail | Vendor cookbook ("Guardrails for LLMs") screens jailbreaks with Noul batteries plus code thresholds. Community: `pi-warden`, `reflex`, `hermes-jev-approvals` (reports 4.4× fewer approval prompts on 153 commands, unverified), `jev-edge` (prompt-injection admission filter) | **Promising, unproven for indirect injection** |
| Robust to adversarial text | **Vendor's own limits page says no:** "State is data, and jev-1.13 does not treat it as hostile by default… an injected instruction… can move the answer." Community list rates gateway abuse scoring "the riskiest idea here". | **Critical limitation** |

### Documented weaknesses that matter for a security product

1. **The judge can itself be steered by the content it judges** (jaggedness #6). This is the same "guardrail injection" risk from our research (doc 02) and pain row 6.
2. **Literal reading** (#1). It answers the question exactly as written, so questions must be precise.
3. **Accuracy drops with long or irrelevant state** (#5). Hard 32k cap per state.
4. **Choice order bias** (#8): it leans toward the first option. Answers must be checked by reordering.
5. **Non-English weaker.** Multilingual attacks are a known evasion technique.
6. **Text only.** Our extractor/OCR must run first (already in our design).
7. **Vendor risk.** A 3-week-old closed model, rate limits changing without notice, and aliases (`jev-latest`) that move. Pin `jev-1.13.0` once thresholds are tuned.

---

## Part C — Should we use it, and where?

### Verdict: **Yes, as one pluggable signal inside the Core Engine. Never as the sole authority.**

Jev's design philosophy is the same as our core principle. TypeSafe's own guardrail cookbook says *"TypeSafe supplies the assessment; your application owns the decision"*, which is our principle P2: rules decide, AI advises. It fits our architecture without reshaping it.

### Where it fits

| Place in our architecture | How Jev is used | Benefit | Guard against its weakness |
|---|---|---|---|
| **Core Engine, detector Tier 2 (AI judge)** | One request per content chunk: **9 Nouls (one per hackathon attack type)** + a "contains instructions aimed at an AI" Noul + a severity Score | All 9 labels in one ~0.1–0.5 s call: directly produces the **F-axis attack-type labels**. Cheap enough to run on *all* untrusted content, not just suspicious content | Runs **after** normalisation and Tier 0/1; its vote is combined with them in rules; disagreement → escalate |
| **Span localisation for neutralisation** | Send a document as an array of chunks with one Noul per chunk | Finds *which* span is malicious, which is exactly what span-level neutralisation needs | Keep chunks small (accuracy falls with state size) |
| **Action Guard, task fit** | State = user's task + proposed tool call; Nouls: "Is this call needed for the task?", "Do its arguments come from retrieved content rather than the user?" | Fast intent-alignment check (our option B) without a slow generative call | Pinned fields and secret scans stay deterministic in code |
| **Graduated response** | Use `confidence` to decide allow / escalate | Fewer, better human prompts; addresses the 93% approval-rate pain | Thresholds set from our own labelled data |
| **Evaluation harness** | Fast secondary grader for borderline outcomes | Cheaper large-scale evaluation | Primary success signal stays deterministic (canary secrets, tool-call logs) |
| **Not used for** | Generating text, neutralised rewrites, red-team attack generation | — | Those stay with free generative LLMs |

### Revised detection cascade (proposal)

```
Tier 0  rules + signatures            (local, free, ms)
Tier 1  local open classifiers        (local, free)
Tier 2  Jev: 9 attack-type Nouls      (~$0.04 per M tokens, ~0.1-0.5 s)   ← new
Tier 3  generative LLM judge          (free tiers: Groq / Gemini) only when Tier 1 and Tier 2 disagree or confidence is low
Policy  deterministic rules combine all signals → ALLOW / NEUTRALISE / BLOCK / ESCALATE
```

The engine talks to a **`DecisionModel` interface**, so Jev, a generative free LLM, or a self-hosted open alternative can be swapped without changing the engine. Several unofficial open re-implementations exist (`openjev`, `jeff`, `decider`, `von`); they're unverified, but they show a self-hosted path for privacy-sensitive customers later.

### Benefits

1. **Labels for all 9 attack types in one call**, which serves the F-axis claim directly.
2. **Speed**: sub-second Tier 2, so lower latency overhead for protected agents.
3. **Cost**: scanning all untrusted content is a few percent of the agent's own cost (to be measured).
4. **Never-malformed outputs**: no JSON-parsing failures in the security path, so better fault tolerance.
5. **Calibrated confidence** feeds escalation thresholds directly, giving fewer and better human prompts.
6. **Ensemble diversity**: a different model family from the LLM judge and local classifiers, so an attack tuned against one is less likely to fool all of them.

### Risks and how we handle them

| Risk | Handling |
|---|---|
| Judge steered by injected text | Never sole authority; combined with local classifiers and rules; the adversary loop specifically targets the judge; "judge disagreement" itself raises risk |
| Paid (no free tier) | Very small spend (see budget below); free generative tiers remain the fallback, so the system still works with no Jev credit |
| Rate limits change without notice | Router with failover to free generative judges; cache; budgets |
| Model updates move answers | Pin `jev-1.13.0`; re-run the evaluation before moving versions |
| Non-English attacks | Measured separately; route to the generative judge when language isn't English |
| Data privacy | Not trained on customer data; offer "no external model" mode (Tier 0/1 only, or self-hosted) for regulated customers later |

### Budget estimate for the hackathon

| Use | Tokens (estimate) | Cost at $0.042/M |
|---|---|---|
| Evaluation corpus, several full runs | ~20–50 M | $0.84–$2.10 |
| Development and demos | ~5 M | $0.21 |
| **Total** | | **≈ $1–3** |

OpenRouter credit is prepaid; a small top-up covers this. **This needs your approval, since you asked for no paid APIs.**

---

## Part D — What changes in our docs if approved

- **PRD (doc 07):** add cost requirements CC1–CC7; add Jev as an optional Tier 2 decision model behind a swappable interface.
- **System design (doc 09) / blueprint / Miro:** detector gains the Jev tier and a "cost and quota" box; the Console gains a cost panel.
- **Validate stage, two new assumptions to test:**
  - **A7:** Jev's recall and false-positive rate on our corpus per attack type, compared with a free generative judge.
  - **A8:** How easily injected text steers Jev's own verdict (judge-injection test).
