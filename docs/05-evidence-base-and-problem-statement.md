# 05 — Evidence Base & Problem Statement v0.2

> Inputs: grokbot `findings.csv` (75 rows) + `report.md` (12 themes), cross-checked against docs 01–02.
> Stage: **Define** → this doc proposes the problem statement for sign-off. ERRC / SCAMPER start only after sign-off.

---

## 1. Audit of grokbot's research

**Verdict: high-quality, usable evidence, with three weaknesses to correct for.**

| Check | Result |
|---|---|
| Every row has URL + date + verification note | ✅ 75/75 |
| Independent spot-check (Claude re-fetched 3 sources) | ✅ 3/3 exact matches: Anthropic auto-mode (rows 56–57), OSFI bulletin (rows 39–40), CSA survey (row 72) |
| Bias flagged | ✅ ~⅓ of rows flagged. **Correction:** the CSA survey (row 72) was *commissioned by Strata*, an identity vendor, so it is biased too (grokbot left this unchecked) |
| Dissent included | ✅ row 19 (tptacek: "close to self-XSS") |
| Honest limits | ✅ no X/LinkedIn, Reddit dates approximate, buyer/procurement voice missing |

**Weaknesses to correct for:**
1. **"Frequency" measures search effort, not prevalence.** One LangChain thread (#35011) supplies five rows (3–7), and grokbot itself says that thread is full of vendor pitches. Theme counts show where the conversation is *visible*, not how common a pain is in industry.
2. **Severity is grokbot's own judgement.** It's reasonable, but "Critical" for the healthcare studies (rows 42–43) reflects controlled research, not deployed incidents.
3. **The detection-failure theme (T2) has zero unflagged practitioner sources.** The evidence is strong research and vendor disclosure, not first-hand operator complaint. It's real, but buyers mostly feel it indirectly.

---

## 2. Hypothesis scorecard (doc 01 assumptions vs. evidence)

| Doc 01 hypothesis | Verdict | Evidence (rows) |
|---|---|---|
| D2: defences break legitimate content (false positives) | ✅ **Confirmed** | 5 ("disable it within a day"), 27 (D&D vs banking), 66 (AgentDojo) |
| S1: agents are a black box to security | ✅ **Confirmed, strongest practitioner signal** | 4, 29, 31, 32, 38, 72 |
| C1: can't approve go-live without assurance | ✅ Confirmed | 13, 36, 40 |
| Gap: detect ≠ neutralise; classifiers bypassed | ✅ Confirmed (research/vendor) | 44, 65, 75 |
| Gap: message-level, not session-level | ✅ Partial | 7 (cumulative queries), 43 (multi-turn) |
| Gap: text-level, not format/channel-aware | ✅ Confirmed | 33 (PDF white text, filter watched only the chat box), 35 |
| Gap: input-only, not action-aware | ✅ **Strongly confirmed** | T3 + T4: 8, 9, 37, 45, 50, 53 |
| Gap: no proof / can't compare claims | ✅ Confirmed | 40, 73; report §d contradiction 2 |
| D3: latency/cost | ⚪ **No evidence found** | — |
| D4/D7: integration friction, vendor lock-in | ⚪ **No direct evidence** | (indirect: 38 "retrofitting is miserable") |
| C2: data residency / privacy of the firewall itself | ⚪ **No evidence found** | — |
| Option C (doc 02): "escalate to a human" as a safety net | ❌ **Challenged** | 56 (93% approval rate), 41 (FSB "rubber-stamping"), 59 (dialog hides payload) |

**What this means:**
- The **unconfirmed** hypotheses (latency, integration friction, privacy) aren't disproven. They're simply not voiced publicly, likely because few teams have deployed a firewall far enough to feel them. Treat them as product constraints to *design* for, not pains to *pitch* on.
- **Human approval is not a safety net.** Any design that leans on "ask the human" must make approvals rare, specific and readable, or it gets rubber-stamped. This changes doc 02 option C.

---

## 3. New insights the research added

1. **The most-cited pain is excess authority, not detection** (T3, rank 1). Agents hold god-mode credentials, and **identity-bearing tool arguments** (customer ID, user ID, API key) stay under model control (rows 8–9). A content-only firewall misses the #1 pain. This is the strongest evidence yet that the boundary must cover **actions and their arguments**, not just incoming text.
2. **What counts as an attack depends on the agent's job** (row 27: "ignore all previous instructions" is an attack in a banking app but legitimate in a D&D game). One universal classifier is the wrong model; judgement has to be **relative to the agent's task and policy**.
3. **Integrity attacks are quieter than exfiltration** (row 31). A manipulated triage decision "doesn't look like an incident until downstream". Leaks aren't the only harm; silent wrong decisions are one too.
4. **Teams must be able to reconstruct a whole session** (row 38: reviewers rejected "we log tool calls"). Observability is a **primary job**, not a supporting feature.
5. **No one owns the composed system** (T10). Model vendor, framework, tool vendor and user each push the risk elsewhere. A layer that sits on the *composition* of model, tools and data has a natural owner gap to fill. (Positioning insight, not a feature.)
6. **The guard itself can be injected** (row 6). This matches doc 02's warning, now from practitioners too.
7. **"Unsolvable" vs "ordinary engineering"** (rows 14/15 vs 19). Our framing should never claim to *solve* prompt injection. The defensible claim is to **reduce what a hijacked agent can do, detect what we can, and prove what happened.**

---

## 4. Consolidated problem clusters (relevance-filtered for our product)

Grokbot's 12 themes regrouped into 4 problem clusters our product could address, plus what's out of scope:

| Cluster | Grokbot themes | Plain-language problem | Maps to P2 attack types |
|---|---|---|---|
| **P-A: Influence.** Untrusted content steers the agent | T1, T2, T5 | Instructions hidden in documents, pages, tickets and tool outputs reach the agent through channels nobody inspects; existing detectors are bypassed by rephrasing or are so noisy they get switched off | Instruction override, role change, encoded, indirect, context poisoning, multi-step |
| **P-B: Blast radius.** A steered agent does real damage | T3, T4, T12 | Agents act with too much authority; identity-bearing arguments are model-controlled; data leaves through channels that look legitimate | Tool abuse, secret extraction, credential theft |
| **P-C: Blindness.** No one can see, reconstruct or prove | T6, T9, (T10) | Security can't see what content influenced which action, can't replay a session, can't compare vendor claims, so agents stall in review or ship with silent exposure | All (evidence layer) |
| **P-D: Friction.** Controls that exist fail in practice | T2 (FP side), T7, T11 | False positives get the control disabled; human approvals get rubber-stamped; strong isolation costs task success | — (utility constraint) |

**Out of scope for v1 (stated honestly as roadmap):**
- Multi-tenant context confusion with **no attacker** (row 37). It's a real problem, but not prompt injection.
- Agent identity / IAM provisioning (part of T3). We **use** least-privilege at the action boundary; we don't become an IAM product.
- Vetting MCP/skill registries before install (T8 supply chain). Malicious *tool descriptions at runtime* are in scope as an input channel; registry scanning is not.

---

## 5. Problem statement v0.2 (for sign-off)

> **Teams putting tool-using AI agents into production cannot stop content they don't control (documents, web pages, emails, tickets, tool and API responses) from steering those agents, cannot limit what a steered agent does with the data and authority it holds, and cannot see or prove afterwards what happened.**
>
> **Today's controls watch the chat box instead of every channel, are bypassed by rephrasing or are so noisy they get switched off, and lean on human approvals that people rubber-stamp, while model vendors, frameworks and tool providers each treat the risk as someone else's. The result: agents either ship with silent exposure, or stall in security review.**

### Structured form

| Element | Content |
|---|---|
| **Who** | Teams that build and operate tool-using LLM agents (primary user), and the security/risk reviewers who must approve them (approver/buyer). See open decision §7. |
| **Situation** | The agent reads untrusted content *and* holds private data *and* can act or send data out (the lethal trifecta). |
| **Problem** | P-A influence · P-B blast radius · P-C blindness, under constraint P-D friction |
| **Why it matters** | OWASP ranks it #1 (LLM01, ASI01); real CVSS 9+ incidents (EchoLeak, ForcedLeak); regulators now name it (OSFI Jul 2026, FSB Jun 2026); security review is the adoption bottleneck (rows 13, 36) |
| **Current alternatives & why they fail** | Classifiers (bypassed: 44, 65, 75), LLM-as-judge (injectable: 6), input-field filters (miss other channels: 33), human approval (fatigue: 56), sandboxes (exfil still possible: 26), "it's the developer's job" (T10) |
| **What solved looks like** | Measured: attack success rate down on a real tool-using agent (static **and** adaptive attacks); false positives low enough that nobody disables it; every decision traceable to the content that caused it; full session replay; approvals rare and readable |
| **Not claimed** | That prompt injection is "solved" (contradiction 1) |

### Sub-problems (revised from doc 01 §6)

| # | Sub-problem | Cluster | Change from v0.1 |
|---|---|---|---|
| SP1 | Recognition across **every channel**, relative to the agent's task | P-A | + channel-awareness, + task-relative judgement (row 27) |
| SP2 | Neutralisation without breaking legitimate content | P-A, P-D | unchanged |
| SP3 | **Containment of actions and their arguments**: authority, identity-bearing parameters, outbound channels | P-B | **elevated to co-primary** (T3 is rank 1) |
| SP4 | **Visibility & proof**: content → decision → action lineage, session replay, comparable evidence | P-C | **elevated to primary** (strongest practitioner voice) |
| SP5 | Adaptability against an attacker who moves second | P-A | unchanged |
| SP6 | Adoption: low-friction integration, approvals that stay meaningful | P-D | + approval-fatigue constraint (row 56) |

---

## 6. Remaining evidence gaps (accepted risk for now)

- **Buyer/procurement voice**: no first-hand security-questionnaire evidence. Hard to get publicly in the time available.
- **India / BFSI practitioner voice**: banking evidence is Canadian (OSFI) and global (FSB) regulators plus one HN commenter. No RBI or Indian-bank evidence yet.
- **Latency, integration friction and privacy**: unvoiced. Design for them, don't pitch on them.
- **In-the-wild exploitation rates**: the public record is mostly disclosed PoCs (report §c).

---

## 7. Primary persona — DECIDED (3 Oct): builder + approver

> **Decision:** primary user = the team that builds and ships the agent; primary approver/buyer = the security reviewer. Problem statement v0.2 is **not yet locked**; the user wants more research or discussion first.

The evidence splits between two personas who want different things:

| | Builders (agent developers / platform leads) | Approvers (security / risk teams) |
|---|---|---|
| Evidence strength | T3, T12, D2 false positives, integration | T6 visibility, T9 review bottleneck, regulators |
| What they want | Low friction, no false positives, no rewrite | Visibility, proof, control, audit replay |
| Who adopts / who pays | Adopts the tool | Signs off / funds it |

**Recommendation:** primary **user** = the team that builds and ships the agent; primary **approver/buyer** = the security reviewer. The product has to win the builder (or it gets disabled, row 5) *and* hand the approver the evidence they need (or the agent stalls, row 36). The two personas are linked: **the builder's job-to-be-done is getting the approver to say yes.**
