# Market, moat, and lessons from two Kaggle competitions

8 Oct 2026. Inputs: a market scan (sources at the end), the problem statements, discussions and winning write-ups of
two Kaggle competitions, and IntentSeal as it is in this repository. Attack content is described at category level
only (D-005, D-014).

## 1. The market in 2026

**Consolidation.** Most venture-backed prompt-security and runtime vendors were bought by security suites:
Lakera (Check Point), Prompt Security (SentinelOne), Protect AI (Palo Alto Networks), CalypsoAI (F5), Robust
Intelligence (Cisco AI Defense), Invariant Labs (Snyk), Aim Security (Cato Networks), Acuvity (Proofpoint), and OpenAI
announced the acquisition of Promptfoo. Buyers now get AI security as a module of a larger platform. One analysis notes
that this leaves a gap for vendors that combine enterprise integration with a permissive licence customers can fork.

| Category | Examples | What it checks | Where it stops |
|---|---|---|---|
| Content classifiers / "LLM firewalls" | Check Point (Lakera Guard), SentinelOne (Prompt Security), Protect AI LLM Guard, Meta Prompt Guard | Text in and out of the model | Detection only. When a paraphrase gets past the classifier, nothing limits what the agent then does |
| Cloud-native guardrails | Azure Prompt Shields, Google Model Armor, AWS Bedrock Guardrails | Prompt attacks, PII and content in that cloud's model calls | Tied to one cloud's models and APIs; no view of the agent's tools, sessions or data flow |
| Programmable guardrail frameworks | NVIDIA NeMo Guardrails, Meta LlamaFirewall, Invariant (Snyk) Guardrails, Guardrails AI | Rules and classifiers the developer writes | A toolkit, not a product. Coverage is whatever the team builds; little evidence or measurement |
| Agent runtime / posture platforms | Zenity, Straiker, Noma, Pillar, Lasso (MCP gateway) | Agent configuration, tool calls, MCP traffic; many focused on coding agents and SaaS agents | Enterprise SaaS, closed, priced for large security teams |
| Research designs | CaMeL (control/data-flow separation), information-flow and data-flow control (DFC, APPA), execution provenance (Agent-Sentry) | Strong guarantees by construction | Require rewriting the agent around a new interpreter or policy language |
| Red teaming / evaluation | promptfoo, garak, HostileShop | Finds failures | Tests, does not protect |

## 2. What IntentSeal does differently

| Capability | Typical classifier / firewall | Typical framework | IntentSeal |
|---|---|---|---|
| Inspects what the agent **reads** (web, PDF, DOCX, email, tool output), including hidden text and OCR | Text only, as given | If the developer wires it | Yes: extraction across 11 channels, hidden-text variants, decoding (CORE-2/3) |
| Checks what the agent **does**, before it runs | No | Rules the developer writes | Yes: deterministic action guard (allow-lists parsed like real clients, pinned fields, outbound secret/canary scan, provenance, session risk) |
| Connects the two (where an argument's text came from) | No | Rarely | Yes: per-session data-flow taint (CORE-17) |
| Keeps working when detection misses | No | Partly | Yes by design: "rules decide, AI advises"; containment does not depend on the classifier or the judge |
| Removes only the malicious part | Usually block/allow | Varies | Neutralise: quarantines spans, keeps the rest (utility) |
| Evidence a security team can use | Logs | Varies | Replayable decision log, approvals, SIEM export, generated evaluation with integrity rules |
| Adoption cost | API call per prompt | Rewrite with the framework | One setting (proxy base URL), a 5-line SDK wrapper, or the REST API |
| Provider and hosting | Vendor cloud | Any | Any model provider (see README), self-hosted, open source |

Weak points to be honest about: held-out false-positive rate above target (10.3% on the previous run), user-turn recall
60.4%, judge-path latency of seconds, single-process scaling, no adaptive-attacker round yet, no hosted SaaS.

## 3. USP and moat

**USP, one line.** IntentSeal keeps an AI agent inside the user's intent: it checks what the agent reads, contains what
the agent does, and proves what happened, with one setting and any model provider.

**What is defensible** (in order of strength):

1. **Containment plus evidence as one system.** Detection is commoditised: every suite has a classifier. Few products
   combine content inspection, action control, data-flow tracking and replayable evidence, and fewer publish an
   end-to-end measurement (attack success off → on, false alarms on a held-out set) with integrity rules.
   That measurement method is a trust advantage that takes others time to copy.
2. **The intent layer.** Pinned fields, provenance, taint and (from this pass) explicit-intent checks for high-risk
   actions express "what the user asked for" as deterministic rules. The Kaggle results below show this is where
   hidden-guardrail designs were weakest.
3. **Breadth of "see what the model sees."** Hidden HTML/PDF/DOCX text, email parts, OCR and encodings are each small,
   together a lot of engineering a competitor has to repeat.
4. **Trainability inside a customer.** Reviewer verdicts become fingerprints that stop the same attack at Tier 0
   without an AI call. Each customer's protection improves with use.
5. **Open, self-hosted, provider-neutral.** After the acquisition wave, buyers who want to avoid lock-in to a security
   suite or a cloud have few independent options.

Not a moat: the classifier, the judge prompt, or any single rule. Those can be copied in weeks.

## 4. Kaggle "AI Agent Security: Multi-Step Tool Attacks" (OpenAI, Google, IEEE; Jun–Sep 2026)

**Task.** Submit an attack algorithm that drives a sandboxed tool-using agent (file, email, web search, shell, HTTP
tools; GPT-OSS 20B and Gemma 4 26B) into security-predicate violations, replayed deterministically against a public
guardrail (source available) and a hidden, stricter private guardrail. Predicates: exfiltration (secret in an HTTP
post), untrusted-to-action (web/email content leads to a privileged action), destructive write (secret file), confused
deputy (email sent without explicit user intent). 4,833 participants.

**What decided the ranking.** Teams that optimised for the public guardrail (secret exfiltration) dropped to zero on
the private guardrail. The private guardrail combined content checks on arguments with provenance: calls carrying the
secret marker were blocked, and privileged actions shortly after a web or email read were blocked. The only attack
family that survived was the confused deputy: an email the user's message did not clearly request. The winner
established that by probing the hidden guardrail, then made that one route as cheap as possible. Others inferred the
hidden guardrail's decisions from replay timing ("replay tomography").

**What the defence could not see** (9th place). The guardrail interface received the tool name, its arguments, recent
sources and tools, the last user message and coarse side-effect labels, but never the tool results. The public
guardrail inspected only the first matching argument name, so a harmless URL argument hid the payload in another
field. A reference "taint tracking" guardrail decided trust from the tool's name rather than from where data came from.
Content scanning and taint tracking failed in opposite directions, so either alone was weak.

**Other recurring techniques** (described by category). Forged chat-template control tokens and forged tool-call or
tool-response turns inside user messages; encodings of the secret (the scorer credited encoded secrets); many
repeated actions per turn; throughput engineering.

### Lessons for IntentSeal

| # | Lesson | IntentSeal today | Action |
|---|---|---|---|
| L1 | Untrusted-to-action and secret-in-argument are blocked by provenance + content checks; **unrequested actions** (confused deputy) were the gap | Provenance and taint cover untrusted targets and copied text, not "did the user ask for this action at all" | Add an explicit-intent rule for high-risk tools (`intent_terms`): no matching request in the user's own words → ESCALATE |
| L2 | Inspect **every** argument, never the first matching name | Outbound scan walks all arguments recursively | Keep; add a regression test |
| L3 | Secrets leave **encoded** | Outbound scan matches literal canaries and secret formats | Decode argument strings (base64, hex, URL, tag characters) before the outbound scan |
| L4 | **Forged role and tool-call markers** (chat-template tokens) inside messages are a primary vector | Not a structural signal | New Tier 0 signal: forged role/template markers in user or untrusted content → judge; the proxy strips them before the model sees them |
| L5 | A defence must see **tool results**, not only tool arguments | The inbound checkpoint inspects every tool result; taint links results to later arguments | Keep as a headline difference |
| L6 | Content checks and provenance fail in opposite directions; **combine** them | Both, plus session risk | Keep; measure each layer's contribution in the evaluation |
| L7 | **The attacker moves second**: adaptive attacks beat static defences | Containment holds when detection misses; no adaptive round yet | EVAL-4 adaptive round is the top evaluation gap (needs the owner's promptfoo account, D-036) |
| L8 | Guardrail decisions leak through timing; classifier scores given to an attacker speed up bypasses | Scores go only to authenticated callers | Never expose scores to untrusted parties; repeated blocks raise session risk (they do) |
| L9 | A shared deterministic benchmark makes defences comparable | Own harness (promptfoo, garak, reference agent) | The competition SDK (MIT, with reference guardrails) could host IntentSeal as a guardrail for an external benchmark; downloading it requires accepting the competition rules (owner action) |

## 5. Kaggle "Red-Teaming Challenge: OpenAI gpt-oss-20b" (Aug 2025)

**Task.** Find up to five previously unreported issues in gpt-oss-20b (reward hacking, deception, sabotage,
inappropriate tool use, data exfiltration, evaluation awareness, chain-of-thought issues), with reproducible findings
and a write-up; judged on severity, breadth, novelty, reproducibility and methodological insight.

**What won.** Methods and tools that generalise, not single jailbreaks:
- *Policy over Values: CoT forgery*: text formatted like the model's own reasoning or policy is treated as
  authoritative ("authority by format"), bypassing the instruction hierarchy; shown to transfer to agentic exfiltration.
- *Don't Trust Yourself* (honourable mention): forged earlier assistant turns change the model's behaviour.
- *HostileShop*: an attacker agent against a shopping agent with "sharp" tools, scored by a deterministic state
  machine instead of an LLM judge; it filters chat-template tags and notes that giving classifier scores to the
  attacker accelerated bypasses.
- *Mind the Gap*: model-level and agent-level vulnerabilities differ; tool-calling contexts were more vulnerable and some
  failures exist only inside the agent loop; action-graph observability explains them.

### Lessons for IntentSeal

- Role and format forgery (reasoning blocks, policy text, prior assistant turns, tool-call syntax) arriving through
  content is a first-class attack vector → L4 above.
- Evaluate at the agent level with deterministic outcome checks, as IntentSeal already does (EVAL-5, end-to-end attack
  success off → on). Model-level classifier scores are not the claim.
- Attacker agents with memory find what static corpora miss → EVAL-4.

## 6. Changes made or planned from this analysis

| Item | Where | State |
|---|---|---|
| Explicit-intent rule for high-risk tools (L1) | action guard, policy `intent_terms` | This pass |
| Decode before outbound scan (L3) | `outbound.py` | This pass |
| Forged role/template markers: signal + strip (L4) | Tier 0, proxy | This pass |
| Every-argument regression test (L2) | tests | This pass |
| Any major model provider, through the proxy and the router | `llm/adapters.py`, proxy, README | This pass |
| Adaptive attacker round (L7) | eval | Owner (D-036) |
| External benchmark via the competition SDK (L9) | eval | Owner decision (rules acceptance) |

## Sources

- Kaggle, AI Agent Security: Multi-Step Tool Attacks: overview, data, discussions, and the 1st, 2nd, 7th, 9th and 11th
  place write-ups (kaggle.com/competitions/ai-agent-security-multi-step-tool-attacks).
- Kaggle, Red-Teaming Challenge: OpenAI gpt-oss-20b: overview, winners, and the write-ups named above
  (kaggle.com/competitions/openai-gpt-oss-20b-red-teaming).
- [AI Security Acquisition Wave (pipelab.org)](https://pipelab.org/blog/ai-agent-security-acquisition-wave-2026/)
- [Best AI Agent Security & MCP Security Platforms for Prompt Injection Protection in 2026 (Nightfall)](https://www.nightfall.ai/blog/prompt-injection-protection)
- [Top AI Agent Firewalls Compared (AgentSwarms)](https://agentswarms.fyi/blog/top-ai-agent-firewalls-comparison)
- [Best AI Agent Security Tools 2026: 24 Options by Boundary (pipelab.org)](https://pipelab.org/blog/best-ai-agent-security-tools-2026/)
- [AI Agent Security Companies: A Six-Control-Plane Market Map (securityopswire)](https://securityopswire.com/ai-agent-security-companies-market-map/)
- [LlamaFirewall (arXiv 2505.03574)](https://arxiv.org/pdf/2505.03574)
- [CaMeL: Defeating Prompt Injections by Design (arXiv 2503.18813)](https://css.csail.mit.edu/6.5660/2026/readings/camel.pdf)
- [Data Flow Control: Data Safety Guarantees for Agents (Columbia DAPLab)](https://daplab.cs.columbia.edu/general/2026/06/26/data-flow-control-data-safety-guarantees-for-agents.html)
- [APPA: Recoverable Information-Flow Control for Real-World LLM Agents (arXiv 2607.24625)](https://arxiv.org/html/2607.24625)
- [Top 5 AI Guardrail Solutions for Production LLM Applications in 2026 (Maxim)](https://www.getmaxim.ai/articles/top-5-ai-guardrail-solutions-for-production-llm-applications-in-2026/)
- Nasr et al., The Attacker Moves Second (arXiv 2510.09023), cited by the 1st-place write-up.
