# 03 — Skills Map, Pain-Point Mining, and Idea Exploration

> Stage: **Define → early Ideate**. Idea directions here are *explorations*, not decisions.
> Order of work: (1) skills reference → (2) mine raw pain points → (3) finalise problem statement → (4) ERRC / SCAMPER / brainstorming against the finalised problem.

---

## Part 1 — Skills reference

### 1A. Attacker-side knowledge (understand it, don't specialise in it)

For a defender, the goal is to **recognise** attack categories and **reproduce them safely inside your own test lab**, not to master offensive tradecraft. Learn these from vetted sources: OWASP, MITRE ATLAS, peer-reviewed benchmarks.

| # | Knowledge area | Why the defender needs it | Vetted sources |
|---|---|---|---|
| A1 | How prompt injection works (direct vs. indirect) | Foundation of the threat model | OWASP LLM01:2025; OWASP LLM Prompt Injection Prevention Cheat Sheet |
| A2 | Attack taxonomy for agents | Shared vocabulary with security teams | OWASP Top 10 for Agentic Applications 2026; MITRE ATLAS |
| A3 | Evasion categories (encoding, obfuscation, multilingual, hidden formatting) | Defenses must normalise content before judging it | OWASP cheat sheet (evasion section) |
| A4 | Agent-specific risk categories (goal hijack, tool misuse, privilege abuse, memory poisoning) | Moves defense from text-checking to behaviour | OWASP AI Agent Security Cheat Sheet; OWASP MCP Security Cheat Sheet |
| A5 | Real incident case studies | Evidence for the problem; realistic test scenarios | Published vendor advisories and CVE write-ups (e.g. CVE-2025-32711 EchoLeak) |
| A6 | Adaptive-attacker thinking | Why static defenses fail; how to evaluate honestly | *The Attacker Moves Second* (USENIX Security 2026) |
| A7 | Benchmark attack suites | Lets us test without inventing attacks by hand | AgentDojo, InjecAgent, BIPIA (use under their licences) |
| A8 | Safe practice environments | Builds intuition legally | Lakera Gandalf; HackAPrompt / Tensor Trust public datasets |

### 1B. Defender skills (where to go deep)

| # | Skill | What it covers | Why it matters for our product | Learn from | Priority |
|---|---|---|---|---|---|
| D1 | **Threat modelling** | Trust boundaries, data-flow diagrams, STRIDE, attack trees, the "lethal trifecta" check | Decides *where* the security boundary sits, which is the most important design choice | Adam Shostack, *Threat Modeling*; OWASP Threat Modeling Cheat Sheet | 🔴 |
| D2 | **Agent architecture security** | Tool-call mediation, least privilege, human-in-the-loop, the six secure design patterns, CaMeL | Containment when detection fails | *Design Patterns for Securing LLM Agents* (2025); CaMeL paper | 🔴 |
| D3 | **Detection engineering** | Normalisation, rules, ML classifiers, LLM judges, ensembles, calibration, thresholds | Core of recognising the 9 attack types | LlamaFirewall paper; Prompt Guard model cards; Sigma/YARA rule concepts | 🔴 |
| D4 | **Content and format parsing** | Extracting *all* text from HTML/PDF/DOCX/images incl. hidden layers; OCR | Hidden content is invisible to text-only filters | PyMuPDF, python-docx, BeautifulSoup docs; Tesseract/PaddleOCR | 🔴 |
| D5 | **Security evaluation & red-team methodology** | Attack success rate, false positives, utility retention, adaptive testing, regression suites | Turns claims into proof (D-axis reliability) | AgentDojo paper; garak, PyRIT, promptfoo docs | 🔴 |
| D6 | **Intent / provenance reasoning** | Does an action follow from the user's task? Where did each piece of data come from? | Catches attacks that look harmless as text | Task Shield, MELON, SIEVE papers | 🔴 |
| D7 | **Policy engines** | Expressing allow/deny rules declaratively, separate from code | Lets security teams own policy | Open Policy Agent (