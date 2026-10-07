# IntentSeal

**Keep AI agents inside the user’s intent.**

A security layer for LLM agents. Everything the agent reads through IntentSeal is inspected; the malicious part is
quarantined where it can be isolated and the content is held where it cannot; every tool call is checked before it
runs; and every decision is recorded so a security team can replay it.

ET AI Hackathon 2026 · Problem 2 (prompt injection). We do not claim to solve prompt injection: we catch what can
be caught, limit what a hijacked agent can do, and prove what happened.

![IntentSeal Console: overview with live evaluation figures](docs/media/console-overview.webp)

- Demo (Security Console): _link added at deployment_
- Video: _link added at submission_
- Evaluation: [docs/EVALUATION.md](docs/EVALUATION.md) (generated from raw results) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

<!-- RESULTS:START -->
### Results (2026-10-07, commit `b4bbcb9-dirty`, generated)

**Grid position by the PRD §15 rule: none / none** (0 of 9 attack types at recall ≥ 85% with FPR ≤ 5%). The self-declaration is the team's decision, made from these numbers.

| Metric | Result |
|---|---|
| Detection recall, third-party content (426 generated attacks through 14 document/data channels; 33 payloads the channel could not deliver excluded) | 96.5% |
| Detection recall, direct user-turn attacks (399 cases) | 60.4% |
| False-positive rate, held-out hard-benign set (39 cases) | 10.3% |
| Fast-path latency p95 (isolated) | 108.8 ms |
| Attack success on the reference agent, `headline` suite (27 / 30 scored tests): off → on | 25.9% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `mt3` suite (40 / 40 scored tests): off → on | 12.5% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `v2e` suite (144 / 144 scored tests): off → on | 0.7% → 0.0% (canary leaks with protection: 0) |
| Attack success on the reference agent, `broad` suite (219 / 219 scored tests): off → on | 4.6% → 0.0% (canary leaks with protection: 0) · protected run from the 5 Oct engine (before fingerprinting); rerun pending |
| Benign task utility retained | 100.0% |
| Security cost per agent cost, `headline` suite (30 protected runs, list prices) | 35% (security tokens per agent token: 1.02) |

Per-type and per-channel numbers, false alarms and method: [docs/EVALUATION.md](docs/EVALUATION.md).
<!-- RESULTS:END -->

## Protect an agent

**Zero code, any language (LLM proxy).** Point the agent's OpenAI-compatible base URL at the gateway:

```bash
OPENAI_BASE_URL=https://<gateway>/proxy/research-agent/v1 OPENAI_API_KEY=<gateway project key> python examples/openai_agent/agent.py
```

User and tool messages are inspected before they reach the model; every tool call the model returns is checked
before the agent sees it (blocked calls become a notice, pinned fields are rewritten).

**Python SDK (deepest protection).**

```python
from intentseal import Guard

guard = Guard("research-agent")                                  # or Guard(..., remote=URL, api_key=KEY)
with guard.session(user_id="u1", task="Summarise my inbox", trusted={"customer_id": "C-1042"}):
    text = guard.inspect(raw_bytes, source="pdf", filename="report.pdf")   # cleaned content or a safe notice

@guard.tool()                                                    # checked before it runs
def send_message(to: str, subject: str, body: str): ...

tools = guard.protect_tools(langchain_tools)                     # LangChain / LangGraph
```

**Gateway API (any language).** `POST /v1/inspect`, `POST /v1/actions/check`, sessions, decisions, replay,
scorecard, approvals, feedback, metrics. OpenAPI at `/docs`.

Policies are YAML per agent (`policies/research-agent.yaml`): allowed tools, pinned fields, recipient and domain
allow-lists, thresholds, session risk, budgets, `monitor` or `enforce` mode.

## How it works

Extract what the model will actually see (hidden PDF/DOCX/HTML text, email parts, OCR) → normalise and decode
(Unicode, look-alikes, base64/hex/tag characters) → known-attack memory → structural rules → local classifier →
free-LLM judge → deterministic policy → quarantine only the offending spans. Actions pass a deterministic guard
(allow-lists, pinned fields, outbound secret/canary scan, provenance, session risk). Rules decide; AI advises.
Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Run it locally

Python 3.11. Commands use the Windows venv layout (`.venv/Scripts/`); on Linux or macOS use `.venv/bin/`.

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.lock
.venv/Scripts/pip install --no-deps -e packages/core -e packages/sdk -e agents -e services/gateway -e eval
cp .env.example .env                          # free-tier provider keys (Groq, Gemini, NVIDIA, OpenRouter)
.venv/Scripts/python -m intentseal_core providers check
.venv/Scripts/python scripts/dev_gateway.py   # API + proxy + demo on :8000 (PORT to change), docs at /docs
.venv/Scripts/python -m pytest -q             # offline test suite
```

Console: `npm --prefix apps/console install && npm --prefix apps/console run dev` (reads `apps/console/.env.development`).

Reproduce the evaluation (needs free-tier keys; about two hours on free quotas): generate attack cases with
`eval/promptfoo/make_configs.py` + `npx promptfoo redteam generate` and harvest garak probes (`eval/garak/run.sh`
notes) → `eval/promptfoo/build_suites.py` → `eval/run_protected.sh` → `python -m intentseal_eval.summary` →
`python -m intentseal_eval.readme`. Each file documents its usage at the top.

## Limitations (honest)

- Free-tier models only. Results depend on today's free models; the judge can be wrong and is never the only authority.
- Attack success is counted only where an outcome is verifiable (sends, canary leaks, fetches, writes, record access), so ASR is a lower bound.
- The generated attack corpus is finite (promptfoo/garak seeds delivered through every channel). No adaptive-attacker round has been run yet.
- Direct user-turn attacks are detected less often than third-party content (user turns keep a fast, weaker filter), and the held-out false-positive rate is above the 5% target; see the results above.
- Images are covered through OCR text only.
- Agent identity, MCP server vetting and non-adversarial data mix-ups are out of scope.

## Credits and licences

All code in this repository was written during the hackathon. Third-party tools, models and data: promptfoo (MIT)
and garak (Apache-2.0) generate the attack cases; ProtectAI DeBERTa v3 prompt-injection classifier (Apache-2.0);
RapidOCR (Apache-2.0); FastAPI, LangGraph, pypdf, pdfplumber, python-docx, BeautifulSoup, ftfy, anyascii,
confusable-homoglyphs, detect-secrets (permissive licences). The Day-1 validation scripts (`eval/validate/`) also
read public Hugging Face datasets and call Llama Prompt Guard 2 through Groq's hosted API (Llama Community License).
Full list: [eval/corpus/LICENSES.md](eval/corpus/LICENSES.md). Our benign evaluation sets are CC-BY-4.0.
