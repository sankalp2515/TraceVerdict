# 06 — Final Problem Statement & Ideation

> Stage: **Define (lock) → Ideate**. Persona decided: builders (users) + security reviewers (approvers).
> Rule for this doc: every pain is a **real, sourced quote** from the grokbot evidence base (`findings.csv`, row numbers), not something we derived. Every clause of the problem statement is traced to the hackathon PDF.

---

## Part A — The problem, in real users' words

| # | Real pain (verbatim) | Who said it | Row |
|---|---|---|---|
| 1 | "Our prompt filter was watching the user input field, not the document upload. The injection came through a content channel our tooling didn't monitor." | Platform lead, after a hidden-text PDF attack | 33 |
| 2 | "If the scanner flags these, developers will disable it within a day." | Agent developer | 5 |
| 3 | "Copilot apparently has classifiers for these, but unsurprisingly these can easily be defeated…" | Analysis of EchoLeak (CVE-2025-32711) | 44 |
| 4 | "LLM-provided kwargs can still override `partial_params`, so `partial_params` alone is not an enforcement mechanism." | Platform lead, regulated billing agent | 8 |
| 5 | "How on earth do I explain to our Security team that the best I can hope for is that I'm asking an LLM nicely to not expose users' secrets to the wrong people?" | Agent developer | 13 |
| 6 | "On audit, 'we log tool calls' didn't survive contact. What they wanted was to reconstruct a full session end to end after the fact." | Platform lead | 38 |
| 7 | "the hardest part isn't getting the agent to work, It's getting the security team comfortable with letting it do anything useful" | Developer / product owner | 36 |
| 8 | "Claude Code users approve 93% of permission prompts… people stop paying close attention to what they're approving." | Anthropic (measured) | 56 |

---

## Part B — Final problem statement

### One sentence
> **Teams can't safely let their AI agents read content from outside — documents, web pages, emails, tool results — because hidden instructions in that content can take over the agent, and today's protections watch the wrong channel, miss reworded attacks, get switched off for false alarms, and leave no evidence of what happened.**

### Full statement
> AI agents now read content that anyone can write (uploaded documents, web pages, emails, API and tool responses) and then act on it with real access to data and tools. Instructions hidden in that content can hijack the agent: make it ignore its task, leak secrets, or misuse its tools.
>
> The teams building these agents have no dependable way to stop this:
> - **Filters watch only the chat box,** while attacks arrive through documents and tool results (pain 1).
> - **Detectors are beaten by rephrasing** (pain 3) or **flag so much legitimate content that developers switch them off** (pain 2).
> - **Once hijacked, the agent can misuse its tools and access**, because the model itself controls what those tools do (pain 4).
> - **Nobody can show the security team what happened** (pains 5, 6), and asking a human to approve every action doesn't work because people stop reading (pain 8).
>
> **The result:** agents either ship with hidden exposure, or stall in security review (pain 7).

### Who
- **Primary user:** the team that builds and ships the agent (developers, platform/ML leads).
- **Approver/buyer:** the security or risk reviewer who must say yes.
- **Link between them:** the builder's real job is getting the reviewer to approve the agent.

### What "solved" looks like (measurable)
1. Attacks hidden in **any** input channel are caught and stripped of their influence; legitimate content still flows.
2. A hijack attempt cannot turn into misuse of the agent's tools or leakage of its secrets.
3. False alarms are low enough that nobody turns the protection off.
4. Every decision can be traced to the exact content that caused it, and a whole session can be replayed for the reviewer.
5. Humans are asked only when it truly matters, with a clear, readable reason.

### What we do NOT claim
That prompt injection is "solved". OWASP, OpenAI and leading researchers say it isn't (rows 54, 69). Our promise: **catch what can be caught, limit what a hijacked agent can do, and prove what happened.**

---

## Part C — Hackathon alignment check (nothing random)

| Problem-statement element | Hackathon PDF requirement it serves |
|---|---|
| "content from outside: documents, web pages, emails, tool results" | **Input sources:** user messages, web pages, PDFs, emails, Markdown, HTML, Word, API responses, OCR text, source code, images via OCR |
| "hidden instructions… take over the agent" | Core mandate: "detect and neutralize malicious instructions embedded in user input or retrieved data **before they influence the AI's behavior**" |
| "watch the wrong channel" → cover every channel | "intercepts **all** incoming content" |
| "get switched off for false alarms" → low false positives | "allowing legitimate content to pass with **minimal disruption**" |
| "miss reworded attacks" → robust detection | Depth axis: "**high degree of demonstrable reliability**" (D2/D3) |
| "leak secrets, misuse its tools" | Attack types 3 Secret Extraction, 4 Tool Abuse, 5 Credential Theft |
| "make it ignore its task" | Attack types 1 Instruction Override, 2 Role Change, 7 Multi-Step Jailbreak |
| "hidden… in documents, tool results" | Attack types 6 Context Poisoning, 8 Encoded Instructions, 9 Indirect Prompt Injection |
| "leave no evidence" → traceability, replay | Supporting features: **observability**; criterion 8 (reliability, human oversight) |
| "humans asked only when it matters" | Criterion 8 (human oversight); event theme "humans in the lead" |
| "AI agents… act with real access" | Event focus on **agentic** systems; criterion 5 |

**Scope boundary (resolves the earlier open question):** limiting what a hijacked agent does with its tools is **in scope**, because three of the nine required attack types (tool abuse, secret extraction, credential theft) are about the agent's *actions*, not its input text. Anything that serves none of the nine types is roadmap.

**Coverage target:** all 9 attack types planned; the F-level claim is made only for types we can **measure** (F3 needs at least 7). Depth claim decided by measured results: D2 on text-based sources, stretching toward D3 on documents and images only if reliability holds.

---

## Part D — Ideation

### D1. Idea sources and how we gathered them

| Source | What it contributed |
|---|---|
| Real pains (Part A, `findings.csv`) | Every idea must answer at least one pain |
| Research defense families (doc 02 §4) | Detect-and-remove, intent alignment, provenance, re-execution, design patterns |
| Market gaps (doc 01 §4.3, doc 02 §3) | What existing guardrails don't do |
| Standards (OWASP LLM01, Agentic Top 10 ASI01–02) | Coverage checklist |
| Analogies from other industries | Email security (sender authentication), web browsers (same-origin rule), banking fraud (score every transaction, ask only on risk), airport security (layered screening), anti-virus (quarantine instead of delete) |
| Our own strengths | Document parsing, verification gates, evaluation discipline |

**Method:** free brainstorm (no judging) → ERRC against today's market → SCAMPER on the standard guardrail → converge by scoring against pains × hackathon fit × feasibility in 8 days.

### D2. Brainstorm (divergent, unjudged)

1. **One checkpoint for every channel**: user messages, files, web, tool results, retrieval and memory all pass through the same inspection.
2. **"See what the model sees"**: before judging a document, reveal everything the model would read (hidden text, metadata, image text), not just the visible part.
3. **Tiered inspection**: fast cheap checks for clean content; deeper analysis only when something looks suspicious.
4. **Surgical neutralisation**: remove or quarantine only the instruction-like part; the rest of the document still flows, clearly labelled as data.
5. **Task-aware judgement**: each agent declares its job; content and actions are judged relative to that job (row 27's banking-vs-game example).
6. **Action checkpoint**: before a tool runs, check the action fits the user's task.
7. **Pinned identity fields**: fields like customer ID or account are always filled from trusted context, never by the model (pain 4).
8. **Outbound secret check**: catch secrets or credentials before they leave in a message, link or tool call.
9. **Origin tracking**: remember which content came from untrusted sources; if an action is built from it, scrutinise harder.
10. **Session memory of risk**: suspicion accumulates across turns, catching attacks split over several steps.
11. **Evidence trail + session replay**: content → decision → action, reviewable by the security team (pain 6).
12. **Security scorecard per agent**: measured catch rate and false-alarm rate on *that* agent; the evidence pack for the reviewer (pains 5, 7).
13. **Monitor mode first**: run alongside without blocking, show what *would* have been caught, then switch to enforcing. Answers "disabled within a day" (pain 2).
14. **Rare, readable approvals**: escalate only high-risk actions, showing exactly what will happen and why (pain 8).
15. **Self-improving adversary**: an internal agent keeps testing the firewall with new variants; every miss becomes a permanent test.
16. **Onboarding scan**: read the agent's tool list and flag risky combinations (private data + outside content + a way to send data out).
17. **Drop-in integration**: wrap an existing agent with a few lines of code, or route through a proxy.
18. *(Opposite idea)* **Shrink the agent instead of filtering content**: reduce what the agent is allowed to do while untrusted content is in play.
19. *(Remove something)* **Never let an LLM judge make the final call alone**: LLM judgement feeds a rule-based decision, so injecting the judge isn't enough (row 6).

### D3. ERRC: versus today's guardrails (classifiers and LLM filters)

| Eliminate | Reduce |
|---|---|
| Single "malicious: 0.93" score with no reason | False alarms (task-aware judgement, monitor mode) |
| Blocking the whole input when one line is bad | Delay on clean content (tiered inspection) |
| Approval prompts for routine actions | Integration effort (drop-in wrapper/proxy) |
| An LLM judge as the sole final authority | Dependence on any one model vendor |

| Raise | Create |
|---|---|
| Channel coverage: every input path, not the chat box | Action checkpoint tied to the user's task, plus pinned identity fields |
| Precision of neutralisation (span-level, not document-level) | Content → action evidence trail with session replay |
| Explanation quality: a readable reason for every decision | Per-agent security scorecard: proof for the reviewer |
| Robustness against reworded/new attacks, measured | Self-improving adversary loop (trainability) |
| Format awareness: what the model actually sees in files | Monitor mode → enforce mode adoption path |

### D4. SCAMPER: on the standard "input classifier" guardrail

| Lens | Idea |
|---|---|
| **Substitute** | Replace "is this text malicious?" with "is this content trying to change what *this* agent does?" (task-aware) |
| **Combine** | Combine input inspection with action checking and origin tracking into one decision |
| **Adapt** | Adapt bank fraud scoring: score every action, ask a human only on high risk |
| **Modify** | Make inspection span-level instead of whole-message; make it session-long instead of one message |
| **Put to other use** | Use the same attack corpus as both the test suite *and* the reviewer's proof (scorecard) |
| **Eliminate** | Remove routine human approvals and the LLM-judge-as-sole-authority |
| **Reverse** | Instead of only filtering what comes *in*, also check what tries to go *out* (secrets, credentials, tool actions) |

### D5. Converge: scoring

Scored 1–3 on: pains answered · hackathon fit · feasible in 8 days at product quality.

| Idea | Pains | Hackathon fit | Feasible | Total | Decision |
|---|---|---|---|---|---|
| 1 Every-channel checkpoint | 3 | 3 | 3 | **9** | Core |
| 2 See what the model sees (files) | 3 | 3 | 2 | **8** | Core |
| 3 Tiered inspection | 2 | 3 | 3 | **8** | Core |
| 4 Surgical neutralisation | 3 | 3 | 2 | **8** | Core |
| 6 Action checkpoint | 3 | 3 | 2 | **8** | Core |
| 7 Pinned identity fields | 3 | 2 | 3 | **8** | Core |
| 8 Outbound secret check | 3 | 3 | 3 | **9** | Core |
| 11 Evidence trail + replay | 3 | 3 | 2 | **8** | Core |
| 15 Self-improving adversary | 2 | 3 | 2 | **7** | Core (also our eval harness) |
| 19 No LLM sole authority | 2 | 3 | 3 | **8** | Core principle |
| 10 Session risk memory | 2 | 3 | 2 | **7** | Core (needed for multi-step) |
| 5 Task-aware judgement | 3 | 2 | 2 | **7** | Core, simple form |
| 12 Security scorecard | 3 | 2 | 2 | **7** | Core, from eval output |
| 13 Monitor mode | 3 | 1 | 3 | **7** | Include (cheap) |
| 14 Rare readable approvals | 2 | 2 | 2 | **6** | Include, minimal |
| 17 Drop-in integration | 2 | 2 | 2 | **6** | Python wrapper only in v1 |
| 9 Origin tracking | 2 | 2 | 1 | **5** | Simple version only |
| 16 Onboarding scan | 2 | 1 | 2 | **5** | Roadmap |
| 18 Shrink the agent | 2 | 1 | 1 | **4** | Roadmap (needs control of the agent) |

### D6. Converged concept (input to the spec)

> **An Agent Security Gateway with three checkpoints and an evidence layer:**
> 1. **Inbound checkpoint**: every piece of incoming content, from any channel, is inspected (including what's hidden in files) and malicious instructions are neutralised at span level while legitimate content flows on.
> 2. **Action checkpoint**: every tool call is checked against the agent's task; identity fields are pinned; secrets and credentials are stopped from leaving.
> 3. **Session layer**: risk is remembered across turns, so attacks split over several steps are caught.
> 4. **Evidence layer**: every decision is explained and traceable; whole sessions can be replayed; a per-agent scorecard proves performance.
> 5. **Adversary loop**: an internal red-team agent keeps testing the gateway, and every miss becomes a regression test.
>
> **Principle:** rule-based, auditable final decisions; AI judgement feeds them but never decides alone.
