# 02 — Research Report: Should a Prompt-Injection Firewall Be "Agentic"?

> Stage: **Define** (still no architecture). Question raised in doc 01 §10.1, re-verified here.
> Audience: product-grade, written for senior engineers and security leaders, not only hackathon judges.
> Research date: 3 Oct 2026. Sources at the end; ⚠ marks claims I could not open in full and took from abstracts or summaries.

---

## 1. TL;DR

1. **Is the issue real? Partly. I overstated it in doc 01 and am revising it.** The PDF's criterion 5 says "*Where relevant*, does the system reason, plan, use tools…". P2 asks for a firewall that *protects* agents. It does not require the firewall *to be* an agent. The ET microsite's own six judging criteria have no separate "agentic" criterion. But the event is the "Agentic Edition", P2 is titled "*Agentic* Cybersecurity", and the brief celebrates systems that "reason, plan, act". A purely passive classifier is therefore an avoidable weakness, not a disqualifier. **Severity: medium. Cost to address: near zero, if we do it the right way.**
2. **For the market, the question matters more than for the hackathon.** In 2026 the industry has moved from "prompt filters" to **agentic runtime security**: session-aware, tool-call-aware, investigation and hunting, adaptive (HiddenLayer, Palo Alto Prisma AIRS, Straiker, Lasso, Check Point). Buyers' guides now say outright that **single-prompt scanning "protects a fraction of the agent"**. A static classifier would be behind the market on day one.
3. **But the research warns that "more agentic" can mean "less secure".** Any LLM that reads attacker text can itself be injected; Meta's LlamaFirewall paper lists "guardrail injection" as a known limitation. Adaptive attackers bypass most heuristic defenses (*The Attacker Moves Second*, USENIX Security 2026). The Design Patterns paper (IBM, Google, Microsoft, ETH and others) concludes that heuristic defenses are "inherently brittle".
4. **Resolution, as a principle rather than a design:** *agentic reasoning around the security decision, never agentic authority that attacker text can steer.* Autonomy belongs where attacker text cannot redirect it: deciding *how deeply* to investigate, checking an agent's actions against the user's *intent*, *adapting* to new attacks through an offline red-team loop, and *escalating to humans*. The final allow/block must stay structured and auditable.
5. **⚠ New rule found during this research (important):** the ET microsite states *"All AI solutions, code, and assets must be **original and developed during the hackathon**."* → **No Veriscope code may be copied, even though it's yours.** Ideas and lessons only. Doc 01 Appendix A has been corrected.

---

## 2. Re-verifying the issue against every official source

| Source | What it says about "agentic" | Implication |
|---|---|---|
| Problem PDF, criterion 5 | "Agentic / Autonomous Capability: **Where relevant**, does the system reason, plan, use tools, take actions, recover from errors, and operate with appropriate autonomy?" | Scored, but the qualifier "where relevant" gives judges discretion for a firewall |
| Problem PDF, P2 text | "AI agents are used… Design a Prompt Injection Firewall that **intercepts all incoming content**" | The firewall protects agents; being an agent is not required |
| PDF, P2 title | "**Agentic** Cybersecurity" | Ambiguous: security *for* agents, or security *by* agents. Both readings exist. |
| ET microsite brief | "harnessing AI systems that can **reason, plan, act, and collaborate**"; "AI can act. Humans provide direction." | Spirit of the event favours agentic behaviour with humans in the lead |
| ET microsite judging (6 criteria) | Relevance, Innovation & Creativity, Technical Implementation, Impact & Scalability, Presentation & Clarity, Business Viability | No separate agentic criterion. Note this differs from the PDF's 8; we must satisfy both lists. |
| ET microsite rules | "must be original and **developed during the hackathon**" | Affects Veriscope reuse (see §1.5) |

**Why ChatGPT didn't raise it:** in its first answer it listed the 8 criteria, including "Agentic/autonomous capability", and warned that "a chatbot with a nice UI is not enough". It never applied that criterion to P2. Once P2 was chosen it framed the product as a gateway or middleware, which is correct positioning but leaves the criterion unaddressed. So the gap was real; my earlier severity ("where most P2 teams will lose points") was too strong. Corrected severity: **medium**.

---

## 3. What the market says (2026)

| Signal | Source | What it tells us |
|---|---|---|
| Vendors now sell **"agentic runtime security"**: detect "multi-step agentic threats… malicious tool calls, data exfiltration", plus "**investigate and hunt** across agentic activity… operationalized into enforceable runtime policies" | HiddenLayer announcement | The category is moving from filter → detection + investigation + policy |
| Buyer's guide: "**Single-prompt scanning will miss the multi-step attack patterns that define 2026**… If a vendor cannot inspect input, output, conversation, RAG content, tool calls, MCP traffic, and session behavior, they are protecting a fraction of the agent." | Straiker "Top 7 runtime platforms" (vendor-authored, so biased, but indicative) | Session- and tool-awareness are now table stakes |
| Inline guardrails "block prompt injection… **under 50 ms, 100+ languages**", across "inputs, tool responses, and multi-turn conversations" | Check Point (owns Lakera) | Performance bar a market product is compared to |
| Prisma AIRS: runtime defense against "prompt injection, tool misuse, **memory manipulation**, data loss" | Palo Alto Networks | Memory/context poisoning is a mainstream buyer concern |
| "Stateful Prompt Firewall… carrying context across the session so an instruction that arrived through ingested data does not get to act with your agent's privileges" | AccuKnox | Even "firewall" products are going stateful |
| **OWASP Top 10 for Agentic Applications (2026)**: ASI01 Agent Goal Hijack, ASI02 Tool Misuse & Exploitation, ASI03 Identity & Privilege Abuse, … memory poisoning, rogue agents | OWASP GenAI | A new standard taxonomy, separate from the LLM Top 10. A market product should map to it. |
| For agents you **inherit** (vendor copilots, third-party agents), design patterns can't be applied; "your options sit **outside the agent**: scoping credentials, constraining network reach, and **baselining what it does at runtime**" | ARMO (Aug 2026) | **Strong validation of the drop-in product thesis**: most enterprises can't rebuild their agents, so a layer outside the agent is the only option |

**Takeaway:** "agentic" in this market means *aware of agent behaviour* (sessions, tool calls, intent, memory) and *able to investigate and adapt*. It does not mean "the firewall is a chatbot".

---

## 4. What the research says

### 4.1 Defense families (2024–2026)

| Family | Representative work | Idea | Strength | Weakness |
|---|---|---|---|---|
| **Input classifiers** | Meta Prompt Guard 2, ProtectAI DeBERTa, LLM Guard | Score each input as injection or not | Fast, cheap | Per-message, brittle vs. adaptive/encoded/indirect attacks |
| **LLM detect-and-remove** | **PromptArmor** (2025) | A guardrail LLM detects *and excises* injected text, then passes clean data on | On AgentDojo: ASR ≈ 0–0.47% with utility up to ~76% ⚠ | It is an LLM reading attacker text, so it's injectable; adaptive results not shown |
| **Reasoning/trajectory auditors** | **LlamaFirewall AlignmentCheck** (Meta, 2025) | Audits the agent's chain of thought for goal hijacking | "Stronger efficacy at preventing indirect injections… than previously proposed approaches" (self-reported, *experimental*) | Paper itself lists **"guardrail injection"** as a risk |
| **Task / intent alignment** | **Task Shield**, **SIEVE** (intent graph + escalation), IPIGuard (tool-dependency graph) | Does each tool call serve the user's original task? | Targets the *action*, not the text | Needs to see tool calls; ambiguous tasks |
| **Behavioural re-execution** | **MELON** (ICML 2025) | Re-run the agent with the user task masked; if it still makes the same tool call, the call was driven by injected data | Labelled "provable", good utility on AgentDojo | Extra LLM calls (cost/latency) |
| **Origin / provenance enforcement** | Routed Origin Policy Enforcement (2026), CaMeL taint tracking | Judge *where data came from*, not its "intent" ("intent is easily manipulated") | Not fooled by clever wording | Needs integration into data flow |
| **Architectural patterns** | **CaMeL** (Google DeepMind 2025); **Design Patterns** paper (6 patterns: action-selector, plan-then-execute, map-reduce, dual LLM, code-then-execute, context-minimisation) | Constrain the agent so untrusted input *cannot* trigger consequential actions | Strongest guarantees | Requires rebuilding the agent; limits utility; argument manipulation still possible |
| **Multi-agent / self-reflective defense** | **AegisLLM** (2025), AutoDefense (2024) | Several cooperating LLM agents (orchestrator, deflector, evaluator…) check inputs/outputs at test time | Adaptive; e.g. 51% improvement on StrongReject ⚠ | Mostly jailbreak/unlearning; multiplies LLM attack surface and cost |
| **Adaptive red-team ↔ guardrail loops** | promptfoo adaptive guardrails, Enkrypt, RL-based automated injection (OpenReview) | Attacks found by automated red teaming feed back into the defenses | Directly addresses "attacker moves second"; gives a living benchmark | Needs a good attack generator; risk of overfitting |

### 4.2 The two papers a senior reviewer will expect us to know

1. **The Attacker Moves Second** (Nasr, Carlini, Tramèr et al.; Anthropic, Google DeepMind, OpenAI, ETH; USENIX Security 2026). Defenses evaluated against static attack strings or weak optimisation don't hold up. *"Future defense work must consider stronger attacks… in order to make reliable and convincing claims of robustness."*
   → **Any reliability number we publish must include adaptive attacks**, or experts will discount it. This directly shapes our D-axis claim.
2. **Design Patterns for Securing LLM Agents** (Beurer-Kellner, Tramèr et al., 2025). *"Once an LLM agent has ingested untrusted input, it must be constrained so that it is impossible for that input to trigger any consequential actions."* General-purpose agents with heuristic defenses are unlikely to "provide meaningful and reliable safety guarantees."
   → Detection alone is never the whole story; **containment of actions** is part of the problem (our SP3).

### 4.3 What this means for "agentic"

- An **agentic defense** (an LLM that reads untrusted content and reasons freely) adds attack surface. That is the main tension.
- The strongest research ideas are agentic **about the protected agent's behaviour** (intent alignment, re-execution, trajectory auditing) or **about the attacker** (adaptive red teaming). They are not "an LLM with tools reading raw attacker text and deciding freely".
- Provenance and intent-based approaches show a direction the market lacks: judge **where data came from and whether the action matches the user's task**, not only "does this text look malicious".

---

## 5. How to pursue the open issue: five legitimate places for autonomy

These are directions to evaluate in the Ideate stage, **not a chosen design**. Each is tested against three questions: *Is it genuinely autonomous? Is it safe (not steerable by attacker text)? Does a customer pay for it?*

| # | Where autonomy lives | What "reason / plan / use tools / act / recover" means here | Safe? | Market value | Evidence it's real |
|---|---|---|---|---|---|
| **A** | **Adaptive investigation (triage depth)**: clean content passes fast; suspicious content triggers a planned set of deeper checks (decode, render hidden text, OCR, compare with task intent, re-execute) | Plans which checks to run, uses analysis tools, stops when confident | ✅ if each check returns structured output and attacker text never chooses the plan | High: lower latency and cost for most traffic, depth only where needed | SOC tiered-triage practice; HiddenLayer "investigate and hunt" |
| **B** | **Intent and action alignment**: before a tool call executes, check whether it follows from the user's original task | Reasons over the agent's trajectory; acts by allowing, blocking or escalating | ✅ mostly; the alignment checker must itself be hardened | Very high: maps to OWASP ASI01/ASI02, catches attacks that detection misses | Task Shield, SIEVE, MELON, LlamaFirewall AlignmentCheck |
| **C** | **Graduated response and recovery, humans in the lead**: choose allow / sanitise / quarantine / require-approval / block; degrade safely when a component fails | Acts proportionally, recovers from errors (fault tolerance), escalates high risk to a human | ✅ when the rules are deterministic and the human has the final say on high risk | High: matches the event theme and enterprise approval needs | OWASP guidance on human approval; microsite "humans in the lead" |
| **D** | **Self-improving red-team loop**: an attacker agent continuously mutates and generates attacks against our own defense; what gets through becomes regression tests and policy updates | Fully agentic: plans attacks, uses tools, evaluates outcomes, iterates | ✅ runs offline / in staging, never on live traffic | Very high: answers "attacker moves second", supplies the **trainability** supporting feature, and *is* our evaluation harness | Nasr et al.; promptfoo adaptive guardrails; RL-based automated injection |
| **E** | **Onboarding / threat-model agent**: reads a customer agent's tools, permissions and data sources, finds lethal-trifecta combinations, drafts a starting policy | Reasons about configuration, produces an actionable plan | ✅ reads trusted configuration, not attacker content | High: solves pain D1 ("I don't know what to defend") and adoption friction | OWASP agentic Top 10; Willison's lethal trifecta |

**Anti-patterns (agent-washing to avoid):**
- An LLM "security agent" with tools that reads raw untrusted content and decides freely. That is the guardrail-injection risk.
- Multi-agent "councils" that only exist to look agentic: more cost and latency, and more LLMs that can be injected.
- Autonomy that silently changes production policy without human review.

---

## 6. Verdict: should we spend time on this?

**Yes, but as a design principle, not a separate workstream.**

- **D (red-team loop)** has to exist anyway: without adaptive testing our reliability claims won't survive expert scrutiny (§4.2). Building it as an agent costs little extra and covers criterion 5, the trainability supporting feature, and the D-axis evidence in one piece of work.
- **B (intent/action alignment)** is where the market and research are heading and where a plain detector falls short. It belongs in the problem scope regardless of the hackathon.
- **A, C, E** are cheap extensions that strengthen adoption, latency and the "humans in the lead" story.

**Guiding principle to carry into Ideate:**
> *Deterministic, auditable enforcement at the boundary. Agentic reasoning around it: how deep to look, whether actions match intent, how to adapt, and when to ask a human. Never give attacker-readable text the power to steer the security decision.*

---

## 7. Impact on our problem definition (updates to doc 01)

1. **Sub-problem SP3 (Containment)** gains weight: research consensus is that detection alone fails against adaptive attackers.
2. **New sub-problem candidate, SP7 "Intent alignment":** knowing whether an agent's action serves the user's task. It may be merged into SP3 during Ideate.
3. **Success metrics:** add *adaptive ASR* (attacks generated against our defense, not only static sets) as a headline metric. Report static and adaptive results separately.
4. **Standards mapping:** a market product should map to **both** OWASP LLM Top 10 (LLM01) and **OWASP Top 10 for Agentic Applications 2026** (ASI01, ASI02, memory poisoning…).
5. **Audience:** positioned as a product for platform/security teams and agent developers. Hackathon judges are one audience among several.
6. **Originality rule:** all product code written fresh from now on.

---

## 8. Open questions for Ideate

1. How many of A–E fit in the build window with product-grade quality? (Likely D + B core, with A/C/E thin.)
2. Can intent alignment (B) work for agents we *don't* control (the drop-in promise), and which integration points make it possible?
3. Where does provenance (origin of data) come from in a drop-in setting?
4. What does the defender LLM see, and how do we keep it from becoming the new injection target?
5. Product scope versus 8 days: what is the *market-ready core* (high quality, narrow) versus the *roadmap* (stated honestly)?

---

## Sources

- Meta, *LlamaFirewall: An open source guardrail system for building secure AI agents* (2025). arXiv 2505.03574; meta-llama.github.io/PurpleLlama/LlamaFirewall
- Debenedetti et al., *Defeating Prompt Injections by Design* (CaMeL), Google DeepMind (2025). arXiv 2503.18813
- Nasr, Carlini, et al., *The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against LLM Jailbreaks and Prompt Injections*, USENIX Security 2026. arXiv 2510.09023
- Beurer-Kellner, Tramèr, et al., *Design Patterns for Securing LLM Agents against Prompt Injections* (2025). arXiv 2506.08837; S. Willison commentary (13 Jun 2025)
- ARMO, *Design Patterns… What Every Pattern Leaves Open* (Aug 2026)
- Shi et al., *PromptArmor: Simple yet Effective Prompt Injection Defenses* (2025). arXiv 2507.15219 ⚠ (numbers via Emergent Mind summary)
- Zhu et al., *MELON: Provable Defense Against Indirect Prompt Injection Attacks in AI Agents*, ICML 2025
- Debenedetti et al., *AgentDojo* (NeurIPS 2024 Datasets & Benchmarks); agentdojo.spylab.ai/results
- *The Task Shield* (2025); *SIEVE* arXiv 2512.06716; *Routed Origin Policy Enforcement* (2026) ⚠ abstracts only
- *AegisLLM: Scaling Agentic Systems for Self-Reflective Defense* (2025), arXiv 2504.20965 ⚠; *AutoDefense* arXiv 2403.04783 ⚠
- OWASP, *Top 10 for Agentic Applications for 2026*; OWASP LLM01:2025
- Vendor pages (biased, used for market signal only): HiddenLayer agentic runtime security; Check Point "Top Agentic AI Security Solutions 2026"; Straiker "Top 7 AI Runtime Security Platforms 2026"; Palo Alto Prisma AIRS; AccuKnox stateful prompt firewall; promptfoo adaptive guardrails
- ET AI Hackathon microsite (economictimes.indiatimes.com/et-spotlight/accenture-ai-hackathon): judging criteria, originality rule
