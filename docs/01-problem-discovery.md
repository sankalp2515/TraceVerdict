# 01 — Problem Discovery: Prompt Injection & Agent Hijacking

> Stage: **Discover → Define** (product lifecycle). No solution design in this document, on purpose.
> Hackathon: ET AI Hackathon — Agentic Edition (Accenture × ET), Problem 2. Deadline 11 Oct 2026, 11:59 PM IST.
> Facts marked ⚠ come from Claude's background knowledge (cutoff-era) — verify the source before quoting them in the deck.

---

## 0. Where we are in the product lifecycle

```
DISCOVER ──► DEFINE ──► IDEATE ──► VALIDATE ──► BUILD ──► TEST ──► LAUNCH ──► ITERATE
   ▲            ▲
 we are here (this doc)
```

| Stage | Question it answers | Output | Time box (8.5 days left) |
|---|---|---|---|
| Discover | Who is attacked, by whom, how, and who suffers? | This doc | Day 1 |
| Define | What exactly is the problem we solve, and how do we know it's solved? | Problem statement + success metrics (§6–§8) | Day 1 |
| Ideate | What could solve it? | Solution options (next doc) | Day 2 |
| Validate | Does the idea actually beat the attacks? | Attack corpus + baseline measurement | Day 2 |
| Build → Test | Working product | Deployed, measured | Days 3–7 |
| Launch | Hackathon submission | Repo, deck, video, public demo | Days 7–8 |

**Confirmed hackathon rules that constrain the product (from the Unstop page + FAQ):**
- Public GitHub repo **and accessible demo links are mandatory** → the product must actually be deployed and reachable, not only run on a laptop.
- All files/links must be publicly accessible and properly named. Late submissions rejected.
- Open-source tools and AI models allowed. Plagiarism = disqualification.
- Self-declared F/D grid position, penalised for over- **and** under-estimating.
- Feature axis = distinct features **+ supporting features (observability, trainability, fault tolerance)**.
- Depth axis = input messiness handled **+ demonstrated reliability of output**.

**What the P2 text does and does not constrain (verified against the PDF wording, 3 Oct):**

| The PDF says | So we are… |
|---|---|
| "detect **and neutralize** malicious instructions embedded in user input or retrieved data **before they influence the AI's behavior**" | **Free in method.** Nothing restricts us to a classifier. The required *outcome* is no influence on behaviour. |
| "intercepts **all** incoming content" | Bound to cover every path content takes into the agent, including tool results and retrieval *inside* the agent loop, not only the front door |
| "allowing legitimate content to pass with **minimal disruption**" | Bound to measure false positives and utility, not only catch rate |
| "The firewall **may** receive: [11 sources]"; "should **try** to detect: [9 types]" | Soft wording. Sources and types are a scope menu; depth (D) rewards handling more heterogeneous sources reliably |
| F1/F2/F3 = "**Detect** at least 2/5/7 types of attacks" | Whatever mechanism stops an attack, the product must still **identify and label the attack type** for it to count on the F-axis |
| Features axis includes supporting features (observability, trainability, fault tolerance) | Product qualities count as features |
| Nothing about tool-call enforcement, policy engines, gateways | **Allowed, not required.** Worth doing only where it strengthens the scored core |

---

## 1. The core weakness being exploited (one paragraph)

Traditional software separates **code** (instructions) from **data**. An LLM receives both as the same thing: text. When an AI agent reads a web page, email, PDF or tool output, nothing in the model *structurally* stops a sentence inside that data from being treated as a command. Every prompt-injection attack is a variation on one idea: **get attacker-written text into the model's context and make it carry the authority of an instruction.** When the model also has tools, that borrowed authority turns into real actions.

---

## 2. Attacker mindset

### 2.1 Who attacks AI agents (personas)

| Persona | Motive | Typical target | Sophistication |
|---|---|---|---|
| **Curious jailbreaker** | Fun, bragging rights, screenshots | Public chatbots | Low–medium; high volume |
| **Bug-bounty / security researcher** | Bounties, reputation, CVEs | Copilots, agent platforms, MCP servers | High; finds novel classes |
| **Cyber-criminal** | Money: data theft, fraud, account takeover | Agents with email/finance/CRM access | Medium–high; automates |
| **Manipulator / "SEO for AI"** | Bias the AI's output (rank my product, pass my résumé, hide negative reviews) | Shopping/hiring/search agents | Low technical, high scale — just hides text in content |
| **Malicious insider** | Data access beyond role, sabotage | Internal RAG / knowledge bases | Low technical, high access |
| **Supply-chain attacker** | Persistent foothold across many victims | Plugins, MCP servers, shared datasets, open-source docs | High |
| **Automated / AI-driven attacker** | Scale | Anything public | Uses LLMs to generate and mutate attacks |

**Key insight:** the most dangerous attacker in an *agentic* world is often **not the user talking to the agent**. It is a third party who never touches the agent and simply plants text where the agent will later read it (indirect injection).

### 2.2 How attackers think — 10 principles

1. **Attack the trust boundary, not the model.** "Where does text I control enter this system?" Every input channel (web, email, file, tool result, memory, RAG store, MCP tool description) is a door.
2. **Look for the "lethal trifecta."** ⚠ (term popularised by Simon Willison, 2025) An agent that has **(a) access to private data + (b) exposure to untrusted content + (c) a way to communicate outward** is exploitable almost by construction. Attackers hunt for agents that combine all three.
3. **The attacker moves second.** Defenders publish a defense; attackers read it and adapt. ⚠ Research from late 2025 ("The Attacker Moves Second", authors from OpenAI/Anthropic/Google DeepMind) reported that adaptive attacks bypassed most published prompt-injection defenses at high success rates. **Static defenses that only pass fixed test sets are not trusted by experts.**
4. **Asymmetry.** The attacker needs one success; the defender must win every time, on every input, forever.
5. **Blend in.** The best payload doesn't look like an attack. It looks like data, a footnote, a formatting note, an email signature, a "note to AI assistants".
6. **Borrow authority.** Fake system messages, fake tool outputs, fake "admin/IT/security team" notices, chat-template tokens, "the user has already approved this".
7. **Turn read access into write access.** The model only "reads"? Then make it *write* something that leaks: a markdown image whose URL carries the secret, a link, a tool call argument, an email draft.
8. **Hide from the detector, not from the model.** Encoding (Base64, hex, ROT13), invisible Unicode, homoglyphs, other languages, white-on-white text, tiny fonts, alt-text, metadata, HTML comments, text inside images. The model can still read it; the filter can't.
9. **Be patient: split and stage.** Spread the payload across turns, documents or tool results so no single piece looks malicious (multi-step / "crescendo" jailbreaks, payload splitting).
10. **Seek persistence.** Poison something the agent will trust again later: long-term memory, the RAG corpus, a shared doc, an MCP tool description that changes after approval ("rug pull").

### 2.3 The agent attack kill chain

| Stage | Attacker action | Example |
|---|---|---|
| 1. Recon | Learn what the agent is, what tools it has, what it reads | Ask it to list tools; extract system prompt; read its docs |
| 2. Weaponize | Write a payload for that agent and goal | "When summarising, also call `send_email` to …" |
| 3. Deliver / Plant | Put payload where the agent will read it | Web page, email to the victim, PR comment, shared PDF, product review |
| 4. Trigger | Victim innocently asks the agent to process it | "Summarise my inbox" |
| 5. Hijack | Model adopts attacker's instruction | Instruction override / role change |
| 6. Act | Agent misuses a tool | Tool abuse |
| 7. Exfiltrate | Data leaves | Secret extraction / credential theft via URL, email, API call |
| 8. Persist | Survive the session | Memory / RAG / context poisoning |

**Mapping the hackathon's 9 attack types onto the chain** — they are not 9 parallel things, they describe different dimensions:

| Dimension | Hackathon attack types | Kill-chain stage |
|---|---|---|
| **Goal** (what attacker wants) | Instruction Override, Role Change, Secret Extraction, Tool Abuse, Credential Theft | Hijack → Act → Exfiltrate |
| **Delivery** (how it gets in) | Indirect Prompt Injection, Context Poisoning | Deliver / Persist |
| **Evasion** (how it hides) | Encoded Instructions | Weaponize |
| **Time** (how it unfolds) | Multi-Step Jailbreak | Hijack (spread over turns) |

A real attack is a **combination**: e.g. *Credential Theft* (goal) × *Indirect via PDF* (delivery) × *Base64* (evasion) × *3 turns* (time). A credible test suite must test combinations, not 9 isolated examples.

### 2.4 Skills attackers possess

| Skill | What it means in practice | Why we must mirror it |
|---|---|---|
| **Reconnaissance of AI systems** | System-prompt extraction, tool enumeration, probing refusals | Defense must assume the attacker knows the system prompt and tool list |
| **Social engineering of models** | Persuasion, urgency, authority, role-play, fake context | Detection by keywords fails; intent matters |
| **LLM internals** | Chat templates/special tokens, tokenization quirks, instruction hierarchy | Payloads using `<\|im_start\|>`, `[INST]`, `System:` etc. |
| **Obfuscation / encoding** | Base64/hex/ROT13, Unicode tags & zero-width chars, homoglyphs, leetspeak, typos, translation | Must normalise/decode before judging |
| **Content-format tricks** | Hidden HTML/CSS, HTML comments, markdown, PDF hidden layers/metadata, DOCX fields, image text, QR codes | Each input source has its own hiding places |
| **Exfiltration channels** | Markdown image URLs, links, tool arguments, DNS/HTTP callbacks, emails | Stopping the *outflow* matters as much as the *inflow* |
| **Agent/tool ecosystem knowledge** | LangChain/LangGraph, MCP, function-calling, browser agents | Attacks target the glue between model and tools |
| **Automation & optimisation** | Fuzzing, LLM-generated attack variants, gradient-based suffixes (GCG), genetic mutation | Defense must be tested against generated variants, not hand-written ones |
| **Persistence techniques** | Memory/RAG poisoning, rug-pull tool descriptions | Content must be checked when *stored*, not only when *used* |
| **Patience / staging** | Multi-turn crescendo, payload splitting | Per-message checks miss session-level attacks |

### 2.5 The attacker's public toolbox (also our testing toolbox)

| Tool / dataset | Type | Use for us |
|---|---|---|
| **garak** (NVIDIA) | LLM vulnerability scanner | Off-the-shelf probes |
| **PyRIT** (Microsoft) | Red-teaming automation framework | Multi-turn attack orchestration |
| **promptfoo** | Red-team + eval CLI | Regression suites |
| **AgentDojo** (ETH Zürich) | Benchmark of agent tasks + injections | Measures attack success *and* task utility together |
| **InjecAgent**, **BIPIA** | Indirect-injection benchmarks | Indirect / tool-output attacks |
| **HackAPrompt**, **Tensor Trust**, **Gandalf** (Lakera) | Crowd-sourced human attack corpora | Realistic human creativity |
| **deepset/prompt-injections** and similar HF datasets | Labelled classifier data | Baseline + benign data |

⚠ Names are well known; confirm licences before redistributing any dataset in our public repo.

---

## 3. Evidence the problem is real (incidents) ⚠ verify each before using in the deck

| Year | Incident | What it shows |
|---|---|---|
| 2023 | Bing Chat ("Sydney") system prompt extracted by users | Secret/system-prompt extraction works on flagship products |
| 2023 | Car-dealership chatbot talked into "agreeing" to sell a car for $1 | Instruction override → business/reputation harm |
| 2024 | Slack AI data-exfiltration via injected instructions in public channels (PromptArmor) | Indirect injection + exfiltration in an enterprise tool |
| 2024 | ChatGPT memory persistent-injection ("SpAIware", J. Rehberger) | Persistence / memory poisoning |
| 2025 | **EchoLeak** — zero-click data exfiltration from Microsoft 365 Copilot via a crafted email (CVE-2025-32711) | Indirect injection, no user action needed, enterprise scale |
| 2025 | GitHub MCP "toxic agent flow" — malicious issue makes agent leak private repo data (Invariant Labs) | Tool abuse via MCP, cross-boundary leakage |
| 2025 | Supabase MCP data leak via support-ticket injection | Lethal trifecta in a real dev tool |
| 2025 | Indirect injection in AI browser agents (e.g. Brave's disclosure on Perplexity Comet) | Web pages hijacking browsing agents |
| 2025 | Gemini hijacked through calendar invites ("Invitation is all you need") | Everyday content as attack vector, physical-world actions |

**Market signal ⚠:** in 2025 major security vendors acquired prompt/AI-security startups — e.g. Check Point→Lakera, Palo Alto Networks→Protect AI, SentinelOne→Prompt Security, F5→CalypsoAI; clouds ship their own (Azure Prompt Shields, AWS Bedrock Guardrails, Google Model Armor). OWASP ranks Prompt Injection **#1 (LLM01:2025)**. → The category has real commercial value and buyers.

---

## 4. Stakeholders and their pain points

### 4.1 Personas

| Persona | Role | What they care about |
|---|---|---|
| **P1 — Agent developer** (startup or product team) | Builds the agent | Ship features fast, don't break UX, low latency, no rewrites |
| **P2 — Platform / ML engineering lead** | Runs many agents across teams | One standard control for all agents, all frameworks, all models |
| **P3 — CISO / security team / SOC** | Owns risk | Visibility, policy, incident evidence, metrics to sign off |
| **P4 — Risk, compliance, legal** (esp. BFSI) | Approves go-live | Audit trail, data residency, regulatory defensibility, human oversight |
| **P5 — Business owner / PM** | Owns the use case | Agent must be useful; security can't kill the product |
| **P6 — End user** | Uses the agent | Their data stays safe; the agent doesn't refuse normal work |

### 4.2 Pain points (hypotheses — to validate)

**Agent developers (P1)**
- D1. *"I don't know what I'm supposed to defend against."* No clear threat model for their specific agent.
- D2. *"Every defense I add breaks legitimate content."* False positives on documents that merely *discuss* security, code with the word "ignore", emails saying "ignore my last email". (Veriscope hit exactly this: a corpus of papers *about* injection.)
- D3. *"Defense adds latency and cost to every call."*
- D4. *"I'd have to rewrite my agent."* Each framework (LangChain, LangGraph, CrewAI, OpenAI/Anthropic SDKs, MCP, custom) has different hook points.
- D5. *"I can't test my own agent."* No ready attack suite for their tools and data; red-teaming is manual.
- D6. *"System-prompt hardening is all I have."* Fragile, model-specific, breaks on model upgrade.
- D7. *"I'm locked to one vendor's guardrail."* Cloud guardrails tie them to that cloud/model.

**Platform leads (P2)**
- L1. Dozens of agents, inconsistent protections, no central control.
- L2. Multiple LLM providers; need one control that works across all.
- L3. Attacks evolve weekly; no way to roll out an update to every agent at once.

**Security teams (P3)**
- S1. *"AI agents are a black box."* No log of what content the agent read, which instruction it followed, which tool it called and why.
- S2. Existing tools (WAF, DLP, email gateways) don't understand natural-language instructions.
- S3. No way to express policy in their own terms ("this agent may never send email to external domains", "never output a secret").
- S4. No incident evidence: when something goes wrong, they can't reconstruct it.
- S5. No metric to sign off: "How protected are we?" has no number.

**Risk / compliance (P4)**
- C1. Can't approve agent go-live without assurance and an audit trail.
- C2. **Data residency & privacy**: sending customer data to a third-party "AI firewall" API is itself a compliance problem (banks, healthcare; India's DPDP Act ⚠).
- C3. Need human-in-the-loop for high-risk actions and proof that it happened.

**Business owners (P5)** — security that blocks too much makes the agent useless; they need to tune strictness per use case.

**End users (P6)** — don't know that opening an email or a web page with their assistant can attack them; get frustrated by unexplained refusals.

### 4.3 Today's alternatives and where they fall short (hypotheses)

| Approach | Examples | Typical gap |
|---|---|---|
| Model alignment / instruction hierarchy | Built into frontier models | Helps, but not a guarantee; out of the deployer's control; varies by model |
| Prompt hardening, delimiters, "spotlighting" | DIY | Fragile; bypassed by adaptive attacks |
| Open-source classifiers | Meta Prompt Guard, ProtectAI DeBERTa, LLM Guard, Rebuff, NeMo Guardrails, Guardrails AI | Mostly text-only, per-message, binary allow/block, English-centric, weak vs. novel/encoded attacks |
| Cloud guardrails | Azure Prompt Shields, Bedrock Guardrails, Model Armor | Vendor/cloud lock-in; data leaves your environment; little agent/tool context |
| Commercial AI firewalls | Lakera, Prompt Security, Protect AI, CalypsoAI, etc. | Closed, costly, now inside large vendors; opaque scoring; limited per-customer proof |

**Recurring gaps (the space a new product could occupy):**
1. **Detect ≠ neutralize.** Most tools say "malicious: 0.93" and block the whole input; few preserve the legitimate part.
2. **Message-level, not session-level.** Multi-step attacks and poisoning over time are missed.
3. **Text-level, not format-aware.** Hidden text in HTML/PDF/DOCX/images is often invisible to the filter.
4. **Input-only, not action-aware.** Don't connect "what the agent read" with "what the agent is trying to do".
5. **No proof.** Customers can't see measured performance on *their* agent and *their* data.
6. **Integration friction & lock-in.**
7. **Privacy.** Many require sending content to a third party.

---

## 5. Jobs-to-be-done

- *When* I deploy an agent that reads outside content and can act, *I want* untrusted content to be unable to take control of it, *so that* I can ship without fearing a breach.
- *When* security asks "are we protected?", *I want* evidence and numbers, *so that* the agent gets approved.
- *When* an attack happens, *I want* to see exactly what came in, what was stopped and why, *so that* I can respond and prove due diligence.
- *When* I add protection, *I want* it to not break legitimate behaviour or add noticeable delay, *so that* users don't notice it.
- *When* I already have agents built, *I want* to protect them without rewriting them, *so that* adoption is cheap.

---

## 6. Problem statement (draft v0.1 — problem only, no solution)

> **Organisations deploying AI agents that read untrusted content and can take actions have no reliable, framework- and model-independent way to stop that content from hijacking the agent — and no way to prove to security and compliance that it is stopped — without breaking legitimate functionality or exposing sensitive data.**

Decomposed into sub-problems:

| # | Sub-problem | Maps to pains | Maps to hackathon |
|---|---|---|---|
| SP1 | **Recognition** — telling malicious instructions apart from legitimate content, including disguised, multi-format, and multi-turn ones | D1, D2, S2 | 9 attack types; D-axis input messiness |
| SP2 | **Neutralisation** — removing attacker influence while keeping legitimate content usable | D2, P5 | "detect **and neutralize** … minimal disruption" |
| SP3 | **Containment** — even if the model is fooled, preventing harmful actions/data leaks | S3, C3 | Tool Abuse, Secret Extraction, Credential Theft; criterion 5 & 8 |
| SP4 | **Visibility & assurance** — logs, explanations, measured performance | S1, S4, S5, C1 | Supporting features (observability); D-axis reliability; criterion 8 |
| SP5 | **Adaptability** — keeping up as attacks evolve | L3, attacker principle 3 | Supporting feature (trainability) |
| SP6 | **Adoption** — fitting into existing agents across frameworks/models, with acceptable latency and privacy | D3, D4, D7, L2, C2 | Market value; criterion 4 & 6 |

### "How might we…" questions
- HMW let an agent use outside content **as information** without ever obeying it **as instruction**?
- HMW remove only the malicious part of a document and keep the rest?
- HMW detect an attack that is spread across several harmless-looking turns or sources?
- HMW stop harm even when detection fails?
- HMW prove protection with numbers a CISO will sign?
- HMW make adding protection to an existing agent a matter of minutes?
- HMW keep sensitive content inside the customer's environment?

---

## 7. Constraints of "blend into any system" (requirements, not design)

What "any AI system" actually spans — the product must face this variety:

| Variation | Range |
|---|---|
| Where untrusted content enters | User message, retrieved RAG chunk, tool/API output, web page, email, file upload, MCP tool description, agent memory, another agent's message |
| Agent frameworks | LangChain, LangGraph, CrewAI, AutoGen, LlamaIndex, OpenAI Agents SDK, Anthropic SDK, MCP clients, custom code |
| Languages | Python, TypeScript/JavaScript (most common), others |
| LLM providers | OpenAI, Anthropic, Google, open-weights/local |
| Deployment | SaaS, self-hosted, on-prem/air-gapped (BFSI) |
| Content formats | Plain text, HTML, Markdown, PDF, DOCX, JSON/API, source code, images/OCR |

Non-negotiable product constraints (derived from pains):
1. **No agent rewrite** to adopt it (D4).
2. **Model-agnostic** (D7, L2).
3. **Low added latency** — must be measured and stated (D3).
4. **Privacy-preserving option** — can run without sending content to a third party (C2).
5. **Explainable decisions** — every block/sanitise has a human-readable reason (S1, S4).
6. **Tunable strictness / policy** per agent (P5, S3).
7. **Defined failure behaviour** — what happens if the firewall itself fails (fault tolerance).
8. **Measurable** — ships with its own evidence (S5).

---

## 8. What "solved" looks like — success metrics (defined before building)

| Metric | Definition | Why |
|---|---|---|
| **Attack Success Rate (ASR)** with vs. without protection | % of attacks that achieve their goal on a real tool-using agent | The only metric that proves "neutralize", not just "detect" |
| **Detection recall per attack type** | % detected, broken down by the 9 types × input source | F-axis claim (≥7 types) |
| **False-positive rate on hard benign content** | % legitimate inputs wrongly blocked/altered — including security articles, code, "ignore my last email" | "Minimal disruption" |
| **Utility retention** | Agent task success with protection on vs. off on benign tasks | Business owner's concern |
| **Adaptive robustness** | ASR against mutated/generated variants not seen during design | Answers "the attacker moves second" |
| **Latency overhead** | p50 / p95 added ms | Developer adoption |
| **Integration effort** | Lines of code / minutes to protect an existing agent | Market value |
| **Explainability coverage** | % decisions with a reason + evidence span | Security/compliance |

These numbers also decide our honest grid claim (F?/D?).

---

## 9. Mapping to the 8 judging criteria

| Criterion | What the problem framing must let us show |
|---|---|
| 1 Significance | Real incidents (§3), OWASP #1, enterprise pains (§4) |
| 2 Innovation | Address the gaps in §4.3 that existing tools leave open |
| 3 Effective AI | AI is central to recognition (SP1) and neutralisation (SP2) |
| 4 Technical execution | Multi-format, multi-turn, measured |
| 5 Agentic capability | **Open question — see §10** |
| 6 Business impact | Pains P1–P6, market signal, adoption effort |
| 7 Prototype quality | Public, deployed, demonstrable |
| 8 Robustness / Responsible AI | Adaptive testing, FP rate, privacy, human oversight, audit trail |

---

## 10. Open questions & assumptions to validate (next stage)

1. **Criterion 5 tension:** a firewall is a guard, not an actor. How does *the firewall itself* show reasoning, planning, tool use, error recovery — without inventing fake agentic theatre?
2. Which input sources and formats appear most in real attacks — where should depth go first?
3. What latency budget is acceptable (likely tens to low hundreds of ms per check)?
4. Is "neutralise and keep the rest" actually safe, or does partial content still carry influence?
5. Which buyer persona do we pitch to judges (Accenture = enterprise / BFSI clients → P3/P4 likely)?
6. What's the honest grid target after we measure a baseline? (Hypothesis F3/D2, stretch toward D3 on documents.)
7. Licensing of public datasets for a public repo.

---

## Appendix A — Veriscope: do we need it?

Prior, pre-hackathon project of the owner (not part of this repository; no code reused, see the originality rule below).

**Verdict: not needed to win. Reuse lessons and patterns, not code.**

| Veriscope asset | Value for P2 | Decision |
|---|---|---|
| `_sanitize_chunk` (nodes.py ~L2527–2578): zero-width strip + chat-template token regex + NL override regex | ~30 lines of regex; tested on 6 attacks / 2 benign — a regression guard, not a benchmark | Take the **ideas** (normalise first; high-precision control tokens; deliberately narrow NL patterns to protect papers *about* injection). Rewrite fresh. |
| Defense-in-depth design (sanitise → fenced `<SOURCE>` framing → verification gate backstop) | Good pattern: "never rely on one layer" | Reuse as a principle |
| LLM router with provider failover, per-key circuit breakers, retry budgets | Directly supports the **fault tolerance** supporting feature | Reuse the pattern only — rewrite from scratch (originality rule below) |
| Prometheus metrics, observability stack | Supports the **observability** supporting feature | Reuse pattern |
| Honest-claims discipline (`VERISCOPE_STRONG_SAFE_DONT_CLAIM.md`) | Exactly what the over/under-claim penalty rewards | Reuse the habit |
| RAG, retrieval, NLI verification of research claims | Not P2's core | Leave |
| Existing free-tier LLM keys (Gemini, OpenRouter, Groq) | Cheap model-agnostic testing | Reuse accounts |

**Originality rule (corrected 3 Oct, see doc 02):** the ET microsite states *"All AI solutions, code, and assets must be original and developed during the hackathon."* → **No Veriscope code is copied, even though it is the user's own.** Only ideas and lessons carry over; every line of the product is written fresh in the new repo.
