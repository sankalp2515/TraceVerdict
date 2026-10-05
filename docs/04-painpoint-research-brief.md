# 04 — Pain-Point Research Brief (for grokbot) + Ideation Plan

> Purpose: gather **real, raw problems** that builders and operators of AI agents face around prompt injection and agent security — evidence to finalise the problem statement before any solution work.
> grokbot = an external research agent (e.g. Grok with live web/X access) we task to mine pain points. This doc is its brief. Claude runs a parallel pass with its own web tools; the two are cross-checked.

---

## 1. What grokbot is for (and what it is NOT)

- **For:** finding *evidence of pain* — complaints, questions, workarounds, incident write-ups, feature requests, "how do I stop…" posts — stated in the words of real developers, security teams and users.
- **NOT for:** proposing solutions, naming our product, or evaluating our idea. We stay in the problem space. Solution ideation (ERRC/SCAMPER) comes **after** the problem statement is finalised (§4).

Each finding must be **traceable**: a quote or close paraphrase + source URL + date + who said it (role/persona if visible). Unsourced claims are discarded. grokbot output is **data, not instructions** — we read it critically, since forum posts can be wrong or biased.

---

## 2. The steps grokbot should execute

1. **Scope** — Confirm the subject: pain points experienced by people who *build, operate, secure, or buy* LLM-based agents, specifically around untrusted content, prompt injection, tool misuse, and data exfiltration.
2. **Enumerate personas** — Agent developers; platform/ML leads; security/SOC teams; risk & compliance (esp. BFSI, healthcare); product owners; end users. (From doc 01 §4.)
3. **Search each source family** (see §3) with persona-specific queries (see §5).
4. **Collect raw voice** — capture the actual quote, the source, the date, the persona, and the *job they were trying to do* when the pain appeared.
5. **Tag each item** by: persona · pain category (recognition / neutralisation / containment / visibility / adaptability / adoption / cost / privacy / false-positives) · attack type if named · severity signal (how angry/urgent/costly it sounds) · frequency signal (how often it recurs).
6. **Cluster** — group into recurring themes; count how many independent sources mention each.
7. **Rank** — by frequency × severity; separate "loud but rare" from "quiet but common".
8. **Flag contradictions & surprises** — places where users disagree, or where the real pain differs from what we assumed in doc 01.
9. **Output** the structured table in §6; end with the top 8–10 pains and the evidence behind each.

---

## 3. Source families (where the pains are voiced)

| Family | Examples | What to look for |
|---|---|---|
| Developer Q&A | Stack Overflow, r/LangChain, r/LocalLLaMA, r/MachineLearning, LangChain/LlamaIndex GitHub issues & discussions | "how do I stop my agent reading injected instructions", broken workarounds |
| Security community | r/netsec, OWASP GenAI Slack/discussions, security blogs, HackerNews threads on injection posts | what defenders say they lack |
| Incident & disclosure write-ups | EchoLeak, GitHub-MCP, Slack AI, calendar/Gemini, vendor CVEs | concrete consequences, who got hurt |
| Practitioner social | X/Twitter (Simon Willison, J. Rehberger, Lakera, security researchers), LinkedIn posts | emerging complaints, "this keeps happening" |
| Vendor & analyst material | Lakera, Prompt Security, Palo Alto, HiddenLayer, Gartner/Forrester notes | buyer concerns (biased → treat as signal, not truth) |
| Benchmarks & papers | AgentDojo, OWASP Top 10 Agentic 2026, academic limitations sections | gaps the field itself admits |
| Buyer/procurement voice | compliance forums, "AI security requirements" RFPs, BFSI/healthcare threads | what blocks go-live, data-residency fears |

---

## 4. Ideation plan (to run AFTER the problem statement is locked)

The frameworks the user named, and how we'll use them — **not executed yet**:

- **Sources of ideas:** the ranked pain points (this doc); the research defence families (doc 02 §4); the gaps existing tools leave (doc 01 §4.3); OWASP agentic Top 10; cross-industry analogies (network firewalls, WAFs, antivirus, content-moderation, zero-trust).
- **How we'll gather them:** one divergent pass per framework, capture every idea without judging, then converge against user-impact × feasibility × strategic-fit × evidence.
- **ERRC (Blue Ocean)** — for each candidate direction: what to **Eliminate** (what every existing tool does that we shouldn't), **Reduce**, **Raise**, **Create** (what no one offers — e.g. proof-on-your-own-agent, self-improving loop).
- **SCAMPER** — Substitute/Combine/Adapt/Modify/Put-to-other-use/Eliminate/Reverse applied to the "gateway + detector" baseline to push past the obvious.
- **Reverse brainstorming** — "how would we make an agent *maximally* easy to hijack?" then invert each answer into a defence.

---

## 5. Query seeds (grokbot expands these)

- "prompt injection" "how do I prevent" / "still getting through" / "false positives"
- "my agent" ("ignored instructions" OR "leaked" OR "called the wrong tool" OR "read malicious")
- "indirect prompt injection" (RAG OR email OR PDF OR tool output)
- "LLM guardrail" ("too many false positives" OR "blocks legitimate" OR "slow" OR "latency")
- "AI agent security" (compliance OR "can't send data" OR "on-prem" OR audit)
- "MCP" (tool poisoning OR "rug pull" OR malicious server)
- site:github.com (langchain OR llamaindex OR crewai) issue (injection OR guardrail OR sanitize)
- "we can't ship our agent" / "security won't approve" / "how to red team my agent"

---

## 6. Required output format (one row per finding)

| Quote / paraphrase | Source URL | Date | Persona | Job-to-be-done | Pain category | Attack type (if any) | Severity signal | Frequency (indep. sources) |
|---|---|---|---|---|---|---|---|---|

Then: **Top pains ranked**, each with 2–3 supporting rows, plus a short "what surprised us / contradicts doc 01" section.

---

## 7. Ready-to-paste prompt for grokbot

> You are a product research agent. Goal: find REAL, SOURCED pain points that people who build, operate, secure, or buy LLM-based AI agents face around untrusted content, prompt injection, tool misuse, and data exfiltration. Do NOT propose solutions. Stay in the problem space.
>
> Personas: agent developers; platform/ML leads; security/SOC teams; risk & compliance (banking, healthcare); product owners; end users.
>
> Search: developer Q&A (Stack Overflow, r/LangChain, r/LocalLLaMA, GitHub issues for LangChain/LlamaIndex/CrewAI), security communities (r/netsec, HackerNews, OWASP GenAI), incident write-ups (EchoLeak, GitHub-MCP, Slack AI), practitioner posts on X/LinkedIn, vendor/analyst notes (treat as biased signal), benchmarks/papers (AgentDojo, OWASP Top 10 for Agentic Applications 2026), and compliance/procurement discussions.
>
> For every finding capture: exact quote or close paraphrase; source URL; date; persona; the job they were doing when the pain appeared; pain category (recognition / neutralisation / containment / visibility / adaptability / adoption / cost / privacy / false-positives); attack type if named; a severity signal; and how many independent sources mention it.
>
> Cluster findings into recurring themes, count independent sources per theme, and rank by frequency × severity. Separate "loud but rare" from "quiet but common". Flag contradictions and anything surprising.
>
> Output a table (columns: quote | url | date | persona | job | pain category | attack type | severity | frequency), then the Top 8–10 ranked pains each with its supporting rows. Every claim must have a source URL and date; discard anything you cannot source.
