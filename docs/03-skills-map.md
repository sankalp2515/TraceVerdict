# 03 — Skills Map (Defender's Competency Checklist)

> Framed as a defender's reference: every offensive technique appears as "what the defender must recognise and neutralise."
> Operational offensive how-to is deliberately kept out of this doc; it belongs in the controlled red-team evaluation harness we build later.
> Priority: 🔴 core to v1 · 🟠 product maturity · 🟢 long-term.

| # | Skill area | What you must understand | Why it matters here | Where to study | Priority |
|---|---|---|---|---|---|
| S1 | Prompt-injection fundamentals | Direct vs. indirect injection; instructions and data sharing one channel | The whole problem rests on this | OWASP LLM01:2025; OWASP Prompt Injection Prevention Cheat Sheet; Simon Willison's series | 🔴 |
| S2 | Threat modelling | STRIDE, attack trees, trust boundaries | Decide where the boundary sits | Shostack, *Threat Modeling*; OWASP threat-modelling cheat sheet | 🔴 |
| S3 | Indirect-injection vectors | How untrusted content reaches an agent: web, email, PDF, RAG, tool output, MCP descriptions | Hardest, most important class | BIPIA / InjecAgent papers; EchoLeak, GitHub-MCP, Slack AI case studies | 🔴 |
| S4 | Obfuscation & encoding recognition | Base64/hex, Unicode tricks, zero-width, homoglyphs, typos, multilingual, split payloads | Normaliser must undo these before judging | OWASP cheat sheet (encoding section) | 🔴 |
| S5 | Document & multimodal content security | Hidden text, metadata, annotations, OCR layers, text-in-images | Covers PDF/image sources; your existing strength | PDF/DOCX basics; multimodal injection papers | 🔴 |
| S6 | Detection engineering | Normalisation, rules, fuzzy/semantic matching, embeddings, lightweight classifiers, LLM-as-judge, ensembles, confidence calibration | The core engine | promptfoo, LLM Guard, Rebuff source; your RAG/eval background transfers | 🔴 |
| S7 | Agent & tool security | Excessive agency, confused deputy, tool-argument manipulation, memory/context poisoning | Catches goal-based attacks at the action, not the text | OWASP Top 10 for Agentic Apps 2026; OWASP AI Agent + MCP cheat sheets | 🔴 |
| S8 | Security evaluation & red-teaming | ASR, false positives/negatives, utility retention, robustness to mutation, latency | Turns claims into measured evidence — what wins | AgentDojo; garak; PyRIT; promptfoo | 🔴 |
| S9 | Web / API security | Auth, authz, sessions, SSRF, request manipulation, content-type confusion | The boundary itself must be secure | OWASP Top 10; PortSwigger Web Security Academy | 🟠 |
| S10 | Production security engineering | RBAC, policy engines, rate limiting, secrets, structured audit logging | Makes it infrastructure, not a demo | FastAPI/Docker/Redis base + security add-ons | 🟠 |
| S11 | Security research habit | Reading disclosures/papers, turning each into a regression test | Answers "attacker moves second"; keeps the product alive | OWASP GenAI; arXiv cs.CR; vendor disclosures | 🟠 |

## Your starting position (from Veriscope + prior work)
Strong already: Python, FastAPI, Docker, Redis, PostgreSQL, LangGraph, RAG, vector search, document/PDF parsing, OCR workflows, NLP, evaluation, system architecture, and — unusually valuable — verification/evidence/deterministic gates.

Gaps to close (in priority order): S3 indirect-injection vectors, S7 agent/tool security, S8 red-team evaluation, S4 obfuscation recognition, then S9 web/API security.

**How the skills get into the build:** the user does not study these deeply; Claude holds them as working knowledge and encodes them into the product and the project skill files. This table is the user's optional orientation + long-term reference.
