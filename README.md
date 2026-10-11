<div align="center">

# IntentSeal

**A prompt-injection firewall for AI agents. Keep agents inside the user's intent.**

[![CI](https://github.com/sankalp2515/intentseal/actions/workflows/ci.yml/badge.svg)](https://github.com/sankalp2515/intentseal/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/intentseal.svg)](https://pypi.org/project/intentseal/)
[![Python](https://img.shields.io/pypi/pyversions/intentseal.svg)](https://pypi.org/project/intentseal/)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

[Quick start](#quick-start) · [How it works](#how-it-works) · [Results](#results) · [Docs](#documentation) · [Contributing](CONTRIBUTING.md)

</div>

IntentSeal sits between an AI agent and everything it reads and does. It inspects every message, web page, document,
email, API response and retrieved passage **before** the model sees it, removes the part that tries to steer the
agent, and checks every tool call **before** it runs. Every decision is recorded, so a security team can replay any
session and see what came in, what was found, which rule decided and what the agent was allowed to do.

![IntentSeal Security Console](docs/media/console-overview.webp)

## Why IntentSeal

- **Sees what the model sees.** Hidden text in PDFs and Word files, CSS-hidden HTML, HTML-only email parts, image text
  (OCR), look-alike letters and encoded payloads (base64, hex, %-encoding, Unicode tags) are extracted, decoded and
  checked, not just the visible text.
- **Enforces what the user authorised.** Each session gets an **intent contract** compiled from the user's own words
  ("research these suppliers, do not contact them"): what is permitted, what is prohibited, what needs an explicit
  request. It is versioned and hash-chained, only the user's words can change it, and every tool call is checked against
  it, so a hijacked agent is stopped even when every detector misses ([assurance](docs/ASSURANCE.md)).
- **Checks actions, not only words.** Allow-lists for tools, recipients, domains and paths; fields pinned to the
  signed-in user; a scan that stops secrets leaving in any argument (also encoded); and data-flow tracing from
  untrusted content into tool arguments.
- **Rules decide, AI advises.** Structural rules and a local classifier first, an AI judge only when needed, and a
  deterministic policy that no model output can override. When detection misses, the action guard still limits what
  a hijacked agent can do.
- **Removes only the attack.** Offending spans are quarantined in place and the rest of the content is kept, so
  legitimate work continues. When an action is stopped, the agent's model is told and carries on another way.
- **Proves the attack path.** For every attempted action the Console shows the chain: the untrusted source, the
  evidence, the proposed call, the rule and contract clause that decided, and whether it ran, backed by the
  application's execution receipt rather than a model's claim.
- **Triages, attacks and repairs itself.** The Investigator, a tool-using agent, turns each flagged session into a
  report with proposals. A red-team loop clusters what got through, mutates it, builds a candidate repair and promotes
  it to a reviewer only when held-out attacks and benign sets prove it helps without new false alarms.
- **Works with your stack.** One base-URL change for any OpenAI- or Anthropic-compatible agent, a Python SDK, or a
  REST API; any model provider; RAG pipelines included.
- **Built for operations.** Monitor mode before enforce, human approvals, session replay, false-alarm feedback that
  is remembered, multi-tenant keys, PostgreSQL, SIEM export (JSON Lines, CEF), Docker image.

It covers the nine common attack types (instruction override, role change, secret extraction, tool abuse, credential
theft, context poisoning, multi-step jailbreaks, encoded instructions, indirect prompt injection) across user
messages, web pages, PDFs, emails, Markdown, HTML, Word documents, API responses, OCR text, source code, images and
retrieved documents. IntentSeal does not claim prompt injection is solved: it catches what can be caught, limits
what a hijacked agent can do, and proves what happened.

## Quick start

### Requirements

| For | You need |
|---|---|
| Option 1 (whole system) | [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine with Compose v2), about 2 GB of free memory (the gateway uses about 1.3 GB), about 3 GB of disk for the image, Git |
| Option 2 (Python package) | Python 3.11 or 3.12 |
| Both | One free model key: [Groq](https://console.groq.com/keys) or [Google AI Studio (Gemini)](https://aistudio.google.com/apikey) |
| Optional | Node.js 18+ (the REST example and Console development), more provider keys for failover (`.env.example`) |

Python dependencies are declared in each package's `pyproject.toml` (`packages/core`, `packages/sdk`,
`services/gateway`) and pinned for reproducible builds in [requirements.lock](requirements.lock); the Console's in
[apps/console/package.json](apps/console/package.json). The engine uses FastAPI, Pydantic, ONNX Runtime with a
DeBERTa-v3 prompt-injection classifier, RapidOCR, pdfplumber and pypdf, python-docx, BeautifulSoup, ftfy and
detect-secrets; nothing else needs installing by hand.

Both options need **one free model key** for IntentSeal's AI judge: [Groq](https://console.groq.com/keys) or
[Google AI Studio (Gemini)](https://aistudio.google.com/apikey), about a minute to create. Without a key IntentSeal
fails closed: content that needs the judge is held, not passed.

### Option 1: the whole system with Docker (about 5 minutes)

Gateway, LLM proxy, Security Console and a protected test assistant with sample files and a labelled attack pack.
Needs [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/sankalp2515/intentseal.git
cd intentseal
cp .env.example .env            # Windows: copy .env.example .env   ·   then set GROQ_API_KEY= (or GEMINI_API_KEY=) in .env
docker compose up --build       # first build takes a few minutes
```

| Open | What you can do |
|---|---|
| http://localhost:8040 | **Test assistant.** Ask *"Summarise test-pack/hidden-text.pdf"* or *"Read my inbox"*: under each answer, *What IntentSeal checked* shows every file, page, message and action with its decision. [The test pack](examples/assistant/test-pack/README.md) lists the attack files (PDF, Word, HTML, email, Markdown, image, API response, code, knowledge base); ordinary files are in `uploads/`, `inbox/` and `kb/` |
| http://localhost:8000 | **Security Console.** Connected agents, decisions by agent, session replay with the attack-to-action chain, the Investigator, results, policy. Reviewer actions (approvals, labels, policy edits, registering agents) ask for `local-admin-key` on the page that needs it |
| http://localhost:8000/docs | **REST API** (OpenAPI) |

**About the attack files.** Every attack in the test pack and in the evaluation was generated by [promptfoo](https://github.com/promptfoo/promptfoo) and [NVIDIA garak](https://github.com/NVIDIA/garak), never written by us, and IntentSeal was never trained on them: the classifier is a public pre-trained model, the judge is a general LLM, and the attack memory starts empty. Your own attack files work the same way: drop them in the assistant's workspace or upload them in the chat.

The local keys (`local-project-key`, `local-admin-key`) work only on this machine; set your own in `.env` for
anything shared ([docs/DEPLOY.md](docs/DEPLOY.md)).

### Option 2: the Python package (about 2 minutes, no Docker)

```bash
pip install "intentseal[embedded]"
intentseal init --agent my-agent --template research-assistant
```

`init` writes a policy and a key file (`~/.intentseal/.env`; it prints both paths). Put `GROQ_API_KEY=...` (or
`GEMINI_API_KEY=...`) in that key file, download an attack file from the test pack, for example
[hidden-text.pdf](examples/assistant/test-pack/hidden-text.pdf), and run:

```python
from intentseal import Guard

guard = Guard("my-agent")                              # or Guard("my-agent", remote="http://localhost:8000", api_key=...)

with guard.session(user_id="u-42", task="Summarise this report"):
    result = guard.inspect_result(open("hidden-text.pdf", "rb").read(), source="pdf", filename="hidden-text.pdf")
    print(result.decision, result.labels, result.policy_rule)     # BLOCK, attack types, the rule that decided

    @guard.tool()                                      # arguments checked before it runs
    def send_message(to: str, subject: str, body: str): ...

    answer = guard.check_output("model answer")        # protected data never reaches the reader
```

**What `pip install` gives you:** the Python SDK and the full detection engine (extraction, OCR, local classifier,
AI judge, policy, action guard, decision log), running inside your Python app. The **gateway** (REST API for any
language, the LLM proxy) and the **Security Console** come with the repository (Option 1).

### Connect your own agent

**LLM proxy** (no code change, any language): point the agent's model client at the gateway. Agents that let you set
a custom OpenAI-compatible endpoint work as they are, for example
[Hermes Agent](docs/INTEGRATION.md#connect-an-existing-agent-hermes-agent).

```bash
OPENAI_BASE_URL=http://localhost:8000/proxy/<agent>/v1           OPENAI_API_KEY=<IntentSeal key>   # OpenAI-compatible clients
ANTHROPIC_BASE_URL=http://localhost:8000/proxy/<agent>/anthropic ANTHROPIC_API_KEY=<IntentSeal key> # Anthropic SDK
```

**Python SDK** (`@guard.tool()` on your tools) or **REST from any language**: the check sits at the tool-execution
boundary, so a tool runs only after IntentSeal allows it, and the application's receipt records that it ran. A
dependency-free Node example: `node examples/node-rest/agent.mjs` (with Docker running).

In the Console, **Agents** lists every connected agent and its activity, registers a new one from a template, gives the
snippet for your stack and runs a self-test.
Step-by-step for teams, RAG apps included: [docs/INTEGRATION.md](docs/INTEGRATION.md).

### Configuration

Everything is set by environment variables in `.env` (copied from [.env.example](.env.example), which documents each
one) and by one policy file per agent in [policies/](policies). The ones that matter first:

| Variable | What it does |
|---|---|
| `GROQ_API_KEY`, `GEMINI_API_KEY` (and `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`) | Model providers for the AI judge; with several, the router fails over between them |
| `INTENTSEAL_API_KEYS` | Gateway keys, `name:key:scope` with scope `project` or `admin` (Docker sets local-only defaults) |
| `INTENTSEAL_PUBLIC_KEY` | Read-only key the Console uses |
| `INTENTSEAL_CANARIES` | Planted fake secrets that must never leave in a tool call or an answer |
| `INTENTSEAL_DATABASE_URL` | PostgreSQL instead of the default SQLite file |
| `INTENTSEAL_SIEM_SINKS` | Push decisions to a JSON Lines file, a webhook or syslog (CEF) |

Every setting, production deployment and operations: [docs/DEPLOY.md](docs/DEPLOY.md).

### API

REST API reference (generated from the app): [docs/API.md](docs/API.md), with a worked example of the three calls an
agent makes (start a session, inspect content, check a tool call) and real responses. Browse every endpoint on the web
without installing anything: [interactive reference (Redoc)](https://redocly.github.io/redoc/?url=https://raw.githubusercontent.com/sankalp2515/intentseal/main/docs/api/openapi.json).
Full OpenAPI schema: [docs/api/openapi.json](docs/api/openapi.json); interactive with "Try it" at
http://localhost:8000/docs when the gateway runs.

## How it works

![IntentSeal in context: untrusted content, your environment, IntentSeal, model provider, security operations](docs/assets/architecture/system-context.svg)

1. **Extract** what the model will actually read: hidden PDF/Word/HTML text, email parts, metadata, OCR.
2. **Normalise and decode**: Unicode repair, look-alike letters, base64, hex, %-encoding, Unicode tags.
3. **Detect** in tiers: known-attack memory and structural rules, a local classifier, then an AI judge (a
   long-context model for long documents).
4. **Decide** with a deterministic policy per agent: allow, neutralise (quarantine the offending spans), escalate to a
   human, or block. Session risk accumulates across turns.
5. **Guard actions**: the session's intent contract (from the user's own words), allow-lists, pinned fields, outbound
   secret scan, provenance and data-flow checks, approvals; execution receipts record what actually ran.
6. **Record** every decision with redacted evidence for the Console, replay and SIEM.
7. **Investigate**: the Investigator agent plans, reads the log, evidence, decoders, attack memory and policy with
   read-only tools, and reports with proposals a reviewer applies.

### Architecture overview

![Component architecture: every integration reaches one core engine](docs/assets/architecture/components.svg)

Five diagrams, each verified against the code, with the files that support every claim:
[docs/diagrams](docs/diagrams/README.md) (system context, components, runtime sequence, security provenance,
evaluation). Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ENGINE.md](docs/ENGINE.md).

## Results

Measured with attacks generated by [promptfoo](https://github.com/promptfoo/promptfoo) and
[garak](https://github.com/NVIDIA/garak), delivered through every input channel, plus hand-written hard benign sets.

<!-- RESULTS:START -->
### Results (2026-10-11, commit `9ca8fb5`, generated)

**All 9 of 9 attack types detected**, recall 61.5%–100.0% by type (0 of 9 also meet the internal target of recall ≥ 85% with FPR ≤ 5%; see [EVALUATION.md](docs/EVALUATION.md)).

| Metric | Result |
|---|---|
| Detection recall, third-party content (359 generated attacks through 14 document/data channels; 31 payloads the channel could not deliver excluded) | 99.2% |
| Detection recall, direct user-turn attacks (442 cases) | 68.1% |
| False-positive rate, held-out hard-benign set (39 cases) | 5.1% |
| Fast-path latency p95 (isolated) | 113.6 ms |
| Attack success on the reference agent, `headline` suite (27 / 30 scored tests): off → on | 25.9% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `v2e` suite (144 / 121 scored tests): off → on | 0.7% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `broad` suite (219 / 157 scored tests): off → on | 4.6% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `mt3` suite (40 / 31 scored tests): off → on | 12.5% → 0.0% (canary leaks with protection: 0) |
| Benign task utility retained | 100.0% |
| Security tokens per agent token, `headline` suite (30 protected runs) | 0.57 |

Per-type and per-channel numbers, false alarms and method: [docs/EVALUATION.md](docs/EVALUATION.md).
<!-- RESULTS:END -->

<!-- ASSURANCE:START -->
### Assurance (generated; engines 8c2b401a4425, 9aca55e22cd6)

| Check | Result |
|---|---|
| **Every detector switched off** (content checks off; the action layer and intent contract alone), `headline` suite on the agent | 0 of 28 attacks succeeded (95% CI 0%–12%); of the 7 attacks that worked unprotected, 6 were stopped by a recorded action block |
| Worst case, deterministic, detectors off: every send or fetch the generated third-party attacks demand | 70 of 70 stopped; each by at least 2 independent rules |
| ... when the attacker targets a party the user named ("Do not email them.") | intent contract 70 of 70; the previous rules 56 of 70 |
| Legitimate sends and writes the user asked for (utility tasks), contract on | 4 of 4 allowed |
| Paired comparison, `headline` (same attacks, both runs completed) | 27 pairs: 26% → 0% (95% CI 0%–12% protected) |
| Repeated trials: the 13 attacks that ever compromised the unprotected agent, 3 runs each | off 15 of 34 trials · on 0 of 37 trials · detectors off 0 of 28 trials compromised |
| Red-team and repair loop on the `v3` suite (168 failures) | variants caught 446/448; held-out failures now caught 29/82; new false alarms 0/615: **PROMOTE (pending reviewer)** |

Reports: `eval/reports/2026-10-11-contract.json`, `2026-10-11-paired.json`, `2026-10-11-redteam.json`. Method: [docs/ASSURANCE.md](docs/ASSURANCE.md).
<!-- ASSURANCE:END -->

**Adaptive attackers.** Two rounds of promptfoo's iterative attackers (crescendo and tree-search jailbreaks over
hijacking, prompt extraction, excessive agency and object-level access), with the first round's misses added to
IntentSeal's attack memory: 0 of 41 scored conversations compromised; IntentSeal flagged 55% and then 63% of them
([report](eval/reports/2026-10-10-adaptive.json); engine of 10 Oct).

**Attacks we never used.** Eleven garak probe families that appear nowhere in our suites or development, typed straight into the chat (the hardest channel): 78 of 105 detected (74%); 46 of 73 (63%) without the invisible tag-character family. Misses: the latent-jailbreak and data-leakage families ([report](eval/reports/2026-10-11-ood.json)).

## Model providers

| Provider | Through the proxy | As IntentSeal's own judge |
|---|---|---|
| OpenAI, Azure OpenAI | ✅ | ✅ |
| Anthropic (Claude) | ✅ native Messages API (thinking, documents, cache control pass through) | ✅ |
| Google Gemini | ✅ native Gemini API (Google Gen AI SDK), or the OpenAI-compatible endpoint | ✅ |
| Groq, Mistral, OpenRouter, NVIDIA NIM, DeepSeek, xAI, Together | ✅ | ✅ |
| Local models: Ollama, vLLM, LM Studio, llama.cpp | ✅ no key needed | ✅ |
| AWS Bedrock, Vertex AI native SDKs | use the SDK or REST API | via an OpenAI-compatible endpoint |

The SDK and REST API inspect content and check tools rather than the model call, so they work with any provider.

## Documentation

| | |
|---|---|
| [Integration guide](docs/INTEGRATION.md) | Proxy, SDK, REST and RAG; who does what; monitor → enforce |
| [Architecture](docs/ARCHITECTURE.md) | Components, data flow, detection tiers, action guard |
| [Engine](docs/ENGINE.md) | Decision flow, rules and thresholds |
| [Deployment](docs/DEPLOY.md) | Docker, Hugging Face Spaces, settings, operations |
| [Evaluation](docs/EVALUATION.md) | Method, per-type and per-channel results, false alarms (generated) |
| [Assurance](docs/ASSURANCE.md) | Intent contracts with detectors bypassed, paired and repeated runs, red-team loop (generated) |
| [Coverage](docs/COVERAGE.md) | The nine attack types across every input source; the F3 · D3 grid (generated) |
| [Architecture diagrams](docs/diagrams/README.md) | Five verified diagrams: context, components, runtime, provenance, evaluation |
| [API reference](docs/API.md) | Every endpoint, generated from the app; OpenAPI schema |
| [Design decisions](docs/DECISIONS.md) | Why the system works the way it does |
| [Test assistant](examples/assistant/README.md) | A real tool-calling assistant to try IntentSeal on your own files |

## Repository layout

```
packages/core        intentseal-core: extraction, detection, policy, action guard, decision log
packages/sdk         intentseal: the Python SDK (embedded or remote)
services/gateway     REST API, LLM proxy (OpenAI, Anthropic and Gemini formats), onboarding, SIEM export, serves the Console
apps/console         Security Console (React)
config               model providers, judge roles, policy templates
policies             example agent policy
examples             test assistant (with a labelled attack test pack), OpenAI and LangGraph agents protected by IntentSeal
agents               reference research agent used by the evaluation
eval                 evaluation harness (promptfoo, garak), benign sets, scenarios, generated reports
tests                offline test suite
```

## Development

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.lock      # .venv/bin on Linux and macOS
.venv/Scripts/pip install --no-deps -e packages/core -e packages/sdk -e agents -e services/gateway -e eval
cp .env.example .env                           # model provider keys
.venv/Scripts/python -m pytest -q              # offline test suite
.venv/Scripts/python scripts/dev_gateway.py    # gateway on :8000
npm --prefix apps/console install && npm --prefix apps/console run dev        # Console
```

Reproducing the evaluation (about two hours on free model tiers): generate attacks with promptfoo
(`eval/promptfoo/make_configs.py`, then `npx promptfoo redteam generate`) and garak (`eval/garak/run.sh`), build the
suites (`eval/promptfoo/build_suites.py`), run `sh eval/run_final.sh`, then `python -m intentseal_eval.summary` and
`python -m intentseal_eval.readme`. Each script documents its usage at the top.

## Limitations

- The AI judge can be wrong; it is never the only authority, and the action guard limits damage when detection misses.
- Direct attacks typed by the user are caught less often than attacks in documents and data (see Results).
- Attack success is counted only where an outcome is verifiable (sends, leaks, fetches, writes, record access), so it is a lower bound.
- Images are covered through their text (OCR).
- Intent contracts read the user's words with a small deterministic grammar: a scoped prohibition ("delete the temp files but not notes.md") applies to the whole capability (conservative), and the contract governs actions, not what the model writes in its answer (the answer check covers secrets).
- Attack success on agents varies run to run with the model; repeated trials and intervals are in [ASSURANCE.md](docs/ASSURANCE.md).
- Very large documents beyond the judge's limits are held rather than passed unchecked; long pages take seconds to assess.
- One gateway process per container (sessions live in the process); use PostgreSQL for shared storage.
- Agent identity, MCP server vetting and non-adversarial data mix-ups are out of scope.

## Contributing

Contributions are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
Please report security issues privately as described in [SECURITY.md](SECURITY.md).

## License

Apache License 2.0, see [LICENSE](LICENSE). Third-party tools, models and data and their licences:
[eval/corpus/LICENSES.md](eval/corpus/LICENSES.md). IntentSeal uses the ProtectAI DeBERTa v3 prompt-injection
classifier (Apache-2.0), RapidOCR (Apache-2.0), and promptfoo (MIT) and garak (Apache-2.0) for evaluation.
