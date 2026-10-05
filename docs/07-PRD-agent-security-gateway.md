# PRD — Agent Security Gateway (Prompt Injection Firewall)

> **Status:** Draft v1.0 for sign-off · **Date:** 4 Oct 2026 · **Owner:** Sankalp (solo) with Claude as engineering team
> **Inputs:** docs/05 (evidence base), docs/06 (final problem statement, ideation). Working name: "Agent Security Gateway" (product name TBD).
> **Hard deadline:** ET AI Hackathon submission **11 Oct 2026, 11:59 PM IST** (public GitHub repo, public demo link, pitch deck, 2–4 min video).

---

## 1. Problem Statement

Teams can't safely let their AI agents read content from outside (documents, web pages, emails, tool results), because hidden instructions in that content can take over the agent. Today's protections watch only the chat box, miss reworded attacks, raise so many false alarms that developers switch them off ("developers will disable it within a day"), and leave no evidence a security team can review ("'we log tool calls' didn't survive contact").

**Who:** teams that build and ship tool-using AI agents (users), and the security reviewers who must approve them (approvers).
**Cost of not solving:** agents either ship with silent exposure (EchoLeak, ForcedLeak: CVSS 9+) or stall in security review ("the hardest part isn't getting the agent to work, it's getting the security team comfortable").
Evidence: docs/05, docs/06 Part A (sourced quotes, `findings.csv`).

---

## 2. Goals

| # | Goal (outcome) | Type | Measured by |
|---|---|---|---|
| G1 | Hidden instructions arriving through **any** supported input channel lose their influence on the agent, while legitimate content still flows | User | Attack success rate (ASR) on the reference agent, with vs. without gateway; utility retention |
| G2 | A hijack attempt cannot become tool misuse or leakage of secrets/credentials | User | ASR for tool abuse / secret extraction / credential theft scenarios |
| G3 | False alarms stay low enough that builders keep it switched on | User (builder) | False-positive rate on a hard benign set |
| G4 | A security reviewer can see, replay and verify every decision | User (approver) | % decisions with reason + source span; % sessions fully replayable; per-agent scorecard produced |
| G5 | Credibly claim **F3** (≥7 of 9 attack types) and a depth level backed by measurement | Business (hackathon) | Per-type detection recall and FPR in the published evaluation report |

---

## 3. Non-Goals

| Non-goal | Why out of scope |
|---|---|
| Claiming prompt injection is "solved" | Not true per OWASP, OpenAI and current research; would be penalised as over-claiming |
| Agent identity / IAM provisioning (issuing scoped credentials) | Separate product category; we enforce at the action boundary instead |
| Vetting MCP servers or skill registries before install | Supply-chain scanning is a separate initiative; malicious tool *descriptions at runtime* are in scope as an input channel |
| Non-adversarial multi-tenant context mix-ups | Real pain, but not prompt injection; roadmap |
| General content moderation (toxicity, harmful content) | Different problem; not in the hackathon's 9 attack types |
| SDKs beyond Python; agents we can't wrap or proxy | Time; Python covers the reference agent and most agent frameworks |
| Training our own foundation/classifier model from scratch | Time; use existing open models + rules + LLM judgement |

---

## 4. User Stories

### Builder (agent developer / platform lead)
1. As an agent developer, I want to protect my existing agent by wrapping it with a few lines of code, so that I don't have to rebuild it.
2. As an agent developer, I want every piece of outside content (uploads, web pages, emails, tool and API results) inspected before my agent sees it, so that attacks can't slip in through a channel I forgot.
3. As an agent developer, I want only the malicious part of a document removed and the rest passed through, so that my agent still does its job.
4. As an agent developer, I want to declare my agent's task and which fields must come from trusted context (e.g. customer ID), so that the model can never change them.
5. As an agent developer, I want secrets and credentials blocked from leaving through a tool call or outgoing message, so that a hijack can't turn into a leak.
6. As a platform lead, I want to run the gateway in monitor mode first and see what it *would* have blocked, so that I can tune it before it affects users.
7. As an agent developer, I want each decision to come with a plain-language reason, so that I can fix false alarms quickly.

### Approver (security / risk reviewer)
8. As a security reviewer, I want to replay a whole agent session (what content came in, what was flagged, what action was taken), so that I can investigate incidents and answer auditors.
9. As a security reviewer, I want a scorecard showing measured catch rate and false-alarm rate for *this* agent, so that I can approve it on evidence instead of vendor claims.
10. As a security reviewer, I want to be asked only about genuinely high-risk actions, with exactly what will happen and why, so that approvals stay meaningful.

### Edge cases
11. As an agent developer, when the gateway's AI component is slow or unavailable, I want a defined safe fallback (rule-based decision, flagged as degraded), so that the agent neither hangs nor silently passes risky content.
12. As an agent developer, when legitimate content merely *discusses* attacks (e.g. a security article), I want it passed through, so that research and security use cases still work.
13. As an agent developer, when an attack is split across several turns, I want the gateway to notice the pattern across the session, so that step-by-step attacks are caught.

---

## 5. Requirements

### P0 — Must-have (cannot ship without)

| ID | Requirement | Acceptance criteria |
|---|---|---|
| **R1 Inbound checkpoint (all channels)** | All incoming content (user message, file, web page, email, API/tool response, retrieved document) passes through one inspection path before reaching the model | - [ ] Each supported channel is routed through the checkpoint in the reference agent<br>- [ ] No channel reaches the model uninspected (verified by a test per channel) |
| **R2 Content extraction ("see what the model sees")** | Before judging, extract all text the model would read from each format: plain text, Markdown, HTML, PDF, DOCX, email, JSON, source code; hidden/non-visible text included | - [ ] Given a document with non-visible text, the extracted view contains that text and marks it as non-visible<br>- [ ] Supported formats listed above each have a passing test |
| **R3 Normalisation** | Undo encodings and obfuscation before detection | - [ ] Encoded-instruction test cases are decoded/normalised before scoring<br>- [ ] Normalisation never alters content passed to the agent except where neutralised |
| **R4 Tiered detection** | Fast rule/classifier tier for all content; deeper AI analysis only when suspicious | - [ ] Clean content completes on the fast tier<br>- [ ] Suspicious content escalates and the tier used is logged |
| **R5 Attack-type labelling** | Every detection is labelled with one or more of the 9 hackathon attack types | - [ ] Each flagged item carries ≥1 label from the 9-type taxonomy<br>- [ ] Labels appear in logs and the scorecard |
| **R6 Span-level neutralisation** | Remove or quarantine only the malicious span; pass the rest, clearly marked as untrusted data | - [ ] Given a document with one malicious span, the agent receives the document minus/quarantining that span<br>- [ ] Benign utility tests still pass |
| **R7 Action checkpoint** | Every tool call is checked against the declared agent task and policy before it runs | - [ ] An injected instruction that tries to call an unrelated tool is blocked and logged with reason<br>- [ ] Task-consistent tool calls are allowed |
| **R8 Pinned trusted fields** | Declared identity-bearing arguments (e.g. user ID, account ID) are always set from trusted context, never by the model | - [ ] A model-supplied value for a pinned field is overridden and logged |
| **R9 Outbound secret/credential check** | Block secrets, credentials and declared sensitive data from leaving via tool arguments, links or outgoing messages | - [ ] Planted canary secrets never leave in any test scenario<br>- [ ] Detection is logged with the attack type |
| **R10 Session risk memory** | Risk accumulates across turns in a session | - [ ] Multi-step test scenarios where no single turn is flagged are caught by session state |
| **R11 Decision log + session replay** | Every decision records input source, extracted span, labels, tier, reason, action taken; sessions can be replayed in order | - [ ] 100% of decisions have a reason and source span<br>- [ ] A session can be replayed end to end in the UI |
| **R12 No sole LLM authority** | Final allow/neutralise/block decisions are made by rule-based policy; AI judgement is an input, never the only gate | - [ ] Architecture and tests show a rule path for every final decision |
| **R13 Fail-safe behaviour** | If the AI tier fails or times out, fall back to the rule tier, flag "degraded", and never pass high-risk content silently | - [ ] Fault-injection test: AI tier down → decisions still made, marked degraded |
| **R14 Reference agent** | A fresh-built research assistant agent with tools: web fetch, file read (PDF/DOCX/HTML/image), database query, file write, send-message (outbound channel) | - [ ] Agent completes benign tasks undefended and defended<br>- [ ] Attacks demonstrably succeed undefended (baseline) |
| **R15 Evaluation harness + report** | Attack and hard-benign corpus covering 9 types × supported channels; measures ASR, recall per type, FPR, utility retention, latency | - [ ] One command reproduces all metrics<br>- [ ] Report published in repo |
| **R23 Zero-code LLM proxy** | OpenAI-compatible endpoint: an agent changes only its API base URL; the proxy inspects incoming messages (user and tool results) and the model's tool calls, then forwards to a free upstream provider | - [ ] An unmodified sample agent is protected by changing only its base URL<br>- [ ] Tool calls that fail the action check are blocked in the proxied response and logged |
| **R16 Public demo + docs** | Deployed, publicly reachable demo; architecture document; README with honest claims | - [ ] Link works from a clean browser<br>- [ ] Architecture doc maps every claimed feature to code and demo |

### P1 — Nice-to-have (fast follow, include if time allows)

| ID | Requirement | Acceptance criteria |
|---|---|---|
| R17 Adversary loop | Internal red-team agent generates new variants against the gateway offline; misses become regression tests | - [ ] Loop run produces new test cases and a before/after metric |
| R18 Per-agent scorecard UI | Reviewer-facing page summarising measured performance for the agent | - [ ] Scorecard renders from latest evaluation run |
| R19 Monitor vs. enforce mode | Toggle to log-only, showing what would have been blocked | - [ ] Same inputs produce identical decisions; only enforcement differs |
| R20 Rare readable approvals | Only high-risk actions escalate, showing the exact action and reason | - [ ] Approval request shows full action arguments in plain language |
| R21 Images via OCR | Extract text from images before inspection | - [ ] Image test cases are inspected via extracted text |
| R22 Drop-in wrapper | Python wrapper/decorator to protect an existing agent's tools and inputs | - [ ] A second, unmodified sample agent is protected with ≤10 lines of change |

### P2 — Future (design for, don't build)
- Proxy/gateway deployment mode for non-Python agents; JS/TS SDK
- MCP-native integration (inspect tool descriptions and traffic at the protocol level)
- Onboarding scan that flags risky tool combinations in a customer's agent
- Full origin/taint tracking through the agent's data flow
- SIEM export (structured security events)
- Self-hosted / on-prem packaging for regulated industries

---

## 6. Hackathon Mapping (grid claim plan)

| 9 attack types | Primary checkpoint | Requirement |
|---|---|---|
| 1 Instruction Override | Inbound | R4–R6 |
| 2 Role Change | Inbound | R4–R6 |
| 3 Secret Extraction | Inbound + outbound check | R4, R9 |
| 4 Tool Abuse | Action checkpoint | R7, R8 |
| 5 Credential Theft | Inbound + outbound check | R4, R9 |
| 6 Context Poisoning | Inbound (retrieved/stored content) | R1, R2, R6 |
| 7 Multi-Step Jailbreak | Session layer | R10 |
| 8 Encoded Instructions | Normalisation | R3 |
| 9 Indirect Prompt Injection | Inbound, all channels | R1, R2 |

**Claim rule:** declare F3 only if ≥7 types meet the recall target with FPR within target on the published evaluation. Declare **D2** (text-based sources, measured reliability) by default; declare **D3** only if documents and images meet the same targets. Supporting features demonstrated: observability (R11), fault tolerance (R13), trainability (R17).

**Judging criteria coverage:** relevance (problem from real pains), innovation (action checkpoint + evidence layer + adversary loop vs. classifier-only market), effective AI (tiered AI judgement), technical execution (R1–R16), agentic capability (tiered investigation, task-aware action checks, adversary loop), business impact (approval bottleneck), prototype quality (public demo), robustness/responsible AI (R12, R13, FPR, honest claims, human oversight).

---

## 7. Success Metrics

Targets are hypotheses to validate on our benchmark; final numbers are reported as measured, not as targets.

### Leading (measured during build, on our evaluation harness)
| Metric | Success | Stretch |
|---|---|---|
| Detection recall per claimed attack type (static corpus) | ≥ 85% for ≥7 types | ≥ 95% |
| ASR on reference agent, defended vs. undefended | ≥ 80% relative reduction | ≥ 95% |
| ASR on adaptive/generated variants (reported separately) | Reported honestly, with trend across loop rounds | Improves each round |
| False-positive rate on hard benign set | ≤ 5% | ≤ 2% |
| Utility retention (benign task success, defended ÷ undefended) | ≥ 90% | ≥ 97% |
| Added latency, fast tier, p95 | ≤ 300 ms | ≤ 100 ms |
| Decisions with reason + source span | 100% | — |
| Canary secrets leaked | 0 | — |

### Lagging (post-hackathon product)
| Metric | Target | When |
|---|---|---|
| External teams trying it (GitHub installs/clones) | 25 | 1 month after launch |
| Agents kept in enforce mode after monitor mode | ≥ 50% of trials | 1 month |
| Design-partner conversations (security reviewers) | 3 | 6 weeks |

---

## 8. Open Questions

| Question | Owner | Blocking? |
|---|---|---|
| ~~Which LLM API keys/budget are available?~~ **Answered 4 Oct:** free tiers only (Groq, Gemini, NVIDIA, OpenRouter, Mistral) + local open models. No paid keys for MVP. | Sankalp | Resolved |
| ~~Product form~~ **Decided 4 Oct:** Core engine + Python SDK + Gateway API + Security Console **+ OpenAI-compatible LLM proxy as a must-have** (new P0, R23) | Sankalp | Resolved |
| Where to host the public demo (free tier acceptable)? | Sankalp + engineering | **Blocking** by Day 6 |
| Product name for repo, deck and demo | Sankalp | Non-blocking (needed by Day 6) |
| Licences of public attack/benign datasets for a public repo | Engineering | Non-blocking (check before publishing corpus) |
| Include images via OCR (R21) in v1, or keep D2-only? | Decide after Day 5 measurement | Non-blocking |
| Exact thresholds for "high-risk" escalation | Engineering | Non-blocking |

---

## 9. Timeline (deadline 11 Oct, 11:59 PM IST)

| Day | Date | Focus | Exit check |
|---|---|---|---|
| 1 | Sat 4 Oct | Spec sign-off · new repo · reference agent skeleton (R14) · corpus v0 (R15) · baseline ASR | Attacks succeed on undefended agent |
| 2 | Sun 5 Oct | R1 inbound path · R2 extraction · R3 normalisation | All channels routed; formats extracted |
| 3 | Mon 6 Oct | R4 tiered detection · R5 labels · R6 neutralisation · R12 policy | First recall/FPR numbers |
| 4 | Tue 7 Oct | R7 action checkpoint · R8 pinned fields · R9 outbound check · R10 session memory | Tool-abuse/secret/credential/multi-step scenarios covered |
| 5 | Wed 8 Oct | R11 log + replay · R13 fail-safe · UI · P1 picks (R19, R18) | Session replay works; degraded mode tested |
| 6 | Thu 9 Oct | R15 full evaluation · R17 adversary loop (if time) · decide grid claim · deploy (R16) | Report generated; public link live |
| 7 | Fri 10 Oct | Architecture doc · README · deck · demo video | All artifacts drafted |
| 8 | Sat 11 Oct | Buffer · final checks (links public, named properly) · **submit by evening** | Submitted well before 11:59 PM IST |

**Cut order if behind schedule:** R17 → R21 → R18 → R20 → R22 → R19. P0 items are not cut. If a P0 slips, reduce the claimed grid level rather than ship an unverified claim.

**Originality:** all code written fresh in the new repo during the hackathon. No Veriscope code is copied.
