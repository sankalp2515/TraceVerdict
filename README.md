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
- **Checks actions, not only words.** Allow-lists for tools, recipients, domains and paths; fields pinned to the
  signed-in user; a scan that stops secrets leaving in any argument (also encoded); "did the user ask for this?" for
  high-risk actions; and data-flow tracing from untrusted content into tool arguments.
- **Rules decide, AI advises.** Structural rules and a local classifier first, an AI judge only when needed, and a
  deterministic policy that no model output can override. When detection misses, the action guard still limits what
  a hijacked agent can do.
- **Removes only the attack.** Offending spans are quarantined in place and the rest of the content is kept, so
  legitimate work continues.
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

**Python SDK** (any model provider):

```bash
pip install "intentseal[embedded]"                    # engine in your process
intentseal init --agent my-agent --template research-assistant
```

```python
from intentseal import Guard

guard = Guard("my-agent")                              # or Guard("my-agent", remote="https://<gateway>", api_key=...)

with guard.session(user_id="u-42", task=user_message):
    page = guard.inspect(html, source="web")           # cleaned content, or a short safe notice
    doc = guard.inspect(pdf_bytes, source="pdf", filename="report.pdf")

    @guard.tool()                                      # arguments checked before it runs
    def send_message(to: str, subject: str, body: str): ...

    answer = guard.check_output(model_answer)          # secrets never reach the reader
```

**LLM proxy** (no code change, any language): point the agent's model client at the gateway.

```bash
OPENAI_BASE_URL=https://<gateway>/proxy/<agent>/v1           OPENAI_API_KEY=<IntentSeal key>   # OpenAI-compatible clients
ANTHROPIC_BASE_URL=https://<gateway>/proxy/<agent>/anthropic ANTHROPIC_API_KEY=<IntentSeal key> # Anthropic SDK
```

**Gateway and Security Console** (Docker):

```bash
docker compose up --build        # gateway (REST API and LLM proxy) on :8000; OpenAPI docs at /docs
```

Then open the Console, **Set up** an agent from a template, copy the snippet for your stack and run the self-test.
Step-by-step for teams, RAG apps included: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## How it works

```mermaid
flowchart LR
    U[User] --> A[Your agent]
    A <-->|model calls| M[Any LLM provider]
    subgraph IntentSeal
      I[Inspect inbound content] --> P{Policy}
      G[Check every action] --> P
      P --> L[(Decision log)]
    end
    W[Web, files, email, APIs, RAG] --> I
    I -->|clean content| A
    A -->|tool call| G
    G -->|allowed, pinned| T[Tools]
    L --> C[Console, SIEM, replay]
```

1. **Extract** what the model will actually read: hidden PDF/Word/HTML text, email parts, metadata, OCR.
2. **Normalise and decode**: Unicode repair, look-alike letters, base64, hex, %-encoding, Unicode tags.
3. **Detect** in tiers: known-attack memory and structural rules, a local classifier, then an AI judge (a
   long-context model for long documents).
4. **Decide** with a deterministic policy per agent: allow, neutralise (quarantine the offending spans), escalate to a
   human, or block. Session risk accumulates across turns.
5. **Guard actions**: allow-lists, pinned fields, outbound secret scan, explicit user intent, provenance and data-flow
   checks, approvals.
6. **Record** every decision with redacted evidence for the Console, replay and SIEM.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/ENGINE.md](docs/ENGINE.md).

## Results

Measured with attacks generated by [promptfoo](https://github.com/promptfoo/promptfoo) and
[garak](https://github.com/NVIDIA/garak), delivered through every input channel, plus hand-written hard benign sets.

<!-- RESULTS:START -->
### Results (2026-10-09, commit `80c9a67`, generated)

**Coverage: 0 of 9 attack types** at recall ≥ 85% with FPR ≤ 5% (level none / none, see [EVALUATION.md](docs/EVALUATION.md)).

| Metric | Result |
|---|---|
| Detection recall, third-party content (427 generated attacks through 14 document/data channels; 32 payloads the channel could not deliver excluded) | 99.8% |
| Detection recall, direct user-turn attacks (426 cases) | 60.1% |
| False-positive rate, held-out hard-benign set (40 cases) | 7.5% |
| Fast-path latency p95 (isolated) | 117.0 ms |
| Attack success on the reference agent, `headline` suite (27 / 30 scored tests): off → on | 25.9% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `v2e` suite (144 / 144 scored tests): off → on | 0.7% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `broad` suite (219 / 231 scored tests): off → on | 4.6% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `mt3` suite (40 / 40 scored tests): off → on | 12.5% → 0.0% (canary leaks with protection: 0) |
| Benign task utility retained | 100.0% |
| Security cost per agent cost, `headline` suite (30 protected runs, list prices) | 19% (security tokens per agent token: 0.96) |

Per-type and per-channel numbers, false alarms and method: [docs/EVALUATION.md](docs/EVALUATION.md).
<!-- RESULTS:END -->

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
| [Design decisions](docs/DECISIONS.md) | Why the system works the way it does |
| [Test assistant](examples/assistant/README.md) | A real tool-calling assistant to try IntentSeal on your own files |

## Repository layout

```
packages/core        intentseal-core: extraction, detection, policy, action guard, decision log
packages/sdk         intentseal: the Python SDK (embedded or remote)
services/gateway     REST API, LLM proxy (OpenAI and Anthropic formats), onboarding, SIEM export
apps/console         Security Console (React)
config               model providers, judge roles, policy templates
policies             example agent policy
examples             test assistant, OpenAI and LangGraph agents protected by IntentSeal
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
