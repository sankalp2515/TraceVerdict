# Architecture inventory and diagram plan

What the diagrams in this folder may claim, and where each claim is verified in the code. Written before the
diagrams were drawn; every box and arrow in them maps to a row here.

## Component inventory

| Component | Source | What it does | Talks to |
|---|---|---|---|
| Core engine | `packages/core/intentseal_core/engine.py` (`Engine`) | The one decision point for every surface: `inspect`, `check_action`, `check_output`, sessions | All modules below |
| Extraction | `extract.py` | Text the model will read from text, Markdown, HTML (incl. hidden), email (HTML-only parts), PDF (incl. white/invisible text), Word (incl. hidden runs), JSON, code, images (OCR via RapidOCR) | Engine (Tier 0) |
| Normalise and decode | `normalise.py`, `decode.py`, `markers.py`, `paste.py` | Unicode repair, look-alike letters, decoding views (base64, hex, %, rot13, tag characters), forged role markers, pasted-material split (D-060) | Engine (Tier 0) |
| Attack memory | `memory.py` | Fingerprints of reviewer-confirmed attacks and false-alarm marks; Tier 0 match | Engine, gateway `/v1/feedback` |
| Tier 1 classifier | `classifier.py` | Local DeBERTa-v3 prompt-injection model (ONNX, CPU), scores every chunk | Engine |
| Tier 2 judge | `decision_model.py`, `llm/router.py` | AI judge (role `judge`, long-context role `judge_long`) through the LLM router with provider failover | Engine; model providers (`config/models.yaml`, `config/providers.yaml`) |
| Policy | `policy.py`, `policies/*.yaml` | Per-agent mode, tools, allow-lists, pinned fields, thresholds, contract, content checks | Engine, action guard, gateway `PUT /v1/policies` |
| Action guard | `action_guard.py` | Tool allowed, pinned fields, outbound scan, recipient/domain allow-lists, sandbox paths, provenance, session risk, intent contract, data flow; worst result wins | Engine (`check_action`) |
| Intent contract | `contract.py` | Per-session contract compiled from the user's words only (D-064) | Engine, action guard, logger |
| Session state | `session.py`, `taint.py` | Risk (user and third-party kept apart), trusted/untrusted entities and their origins, data-flow fingerprints, contract | Engine, action guard |
| Outbound and answer check | `outbound.py`, `secrets.py`, `Engine.check_output` | Canaries, registered secrets and secret formats in arguments and answers, also encoded | Action guard, engine |
| Decision logger | `logger.py`, `store.py`, `siem.py` | Events, findings, decisions, actions, approvals, contracts, receipts in SQLite or PostgreSQL; SIEM records (JSON Lines, CEF) | Gateway readers, SIEM sinks |
| Python SDK | `packages/sdk/intentseal/guard.py`, `remote.py`, `langchain.py` | `Guard`: embedded engine or `RemoteEngine` (HTTP to the gateway); `@guard.tool()`; `protect_tools` for LangChain/LangGraph | Engine (embedded) or REST API (remote) |
| Gateway REST API | `services/gateway/intentseal_gateway/app.py`, `security.py`, `tenancy.py` | `/v1/inspect`, `/v1/actions/check`, `/v1/outputs/check`, `/v1/sessions`, evidence, policy, approvals, memory, provenance, receipts; scoped keys, rate limits | Engine, logger |
| LLM proxy | `proxy.py`, `proxy_gemini.py` | OpenAI-compatible, Anthropic Messages and Gemini formats: user messages and tool results inspected before the model, returned tool calls checked before the agent, answers checked | Engine; upstream model provider |
| Investigator | `investigator.py` | Tool-using triage agent over the log (read-only tools); proposals a reviewer applies | Logger/store, LLM router |
| Provenance | `provenance.py` | Attack-to-action chains from the log, contracts and receipts (D-065) | Logger/store |
| Console | `apps/console` | React UI served by the gateway at `/`: decisions, replay with provenance, review, policy, set-up | Gateway API (public / reviewer key) |
| Evaluation | `eval/` | promptfoo/garak suites, agent target with protection arms, deterministic scoring, summary, paired, contract, red-team, grid | Engine (through the SDK), reference agent `agents/research_agent` |

## What the diagrams must not imply

- **The proxy is not a full interceptor.** It sees what passes through model calls: user messages, tool results the
  agent sends back, tool calls the model returns, the answer. It cannot see a file the agent reads without returning it
  to the model, or a side effect the agent performs without a tool call (`proxy.py` module docstring).
- **The SDK and REST check only what the application routes through them.** `@guard.tool()` and `protect_tools` guard
  the wrapped tools; the application decides what else to inspect.
- **Execution receipts are reported by the application.** Proxy-connected agents send none; "not executed" there rests
  on the enforced decision (the call is removed from the model's response).
- **The model provider is reached two ways:** through the proxy (the gateway forwards the call) or directly by an SDK
  or REST application (IntentSeal only inspects and checks).
- **The AI models advise.** The Tier 1 classifier and the Tier 2 judge produce scores; the deterministic policy
  decides (`engine.py` decision block, D-011).

## Diagram plan

| # | Diagram | Audience | Question it answers | Components | Verified in |
|---|---|---|---|---|---|
| 1 | System context | Executives, judges, buyers | Where does IntentSeal sit, and what does it protect? | User, agent, untrusted sources, IntentSeal, model providers, tools, security operations | `proxy.py` (docstring), `guard.py`, `app.py` (routes), `logger.py`, `siem.py` |
| 2 | Component architecture | Engineers, architects | Which parts exist, and how does each integration reach the one engine? | Proxy (3 formats), REST API, SDK (embedded/remote), LangChain helper, core engine modules, router, store, Console, Investigator, provenance | `proxy.py`, `proxy_gemini.py`, `app.py`, `guard.py`, `remote.py`, `langchain.py`, `engine.py`, `llm/router.py`, `logger.py` |
| 3 | Runtime sequence | Engineers, security reviewers | What happens, in order, when an agent reads content and then tries to act? | User, agent, engine (inspect, decide, action guard, contract), judge, tool, log | `engine.py` (`start_session`, `_inspect`, `check_action`), `action_guard.py`, `guard.py` (`tool`), `app.py` (receipt) |
| 4 | Security provenance | Security teams, auditors | How did untrusted content reach an attempted action, what stopped it, and did it run? | Untrusted source, evidence, session records, proposed call, checks, decision, outcomes, log, provenance chain | `taint.py`, `session.py` (`entity_origin`), `action_guard.py`, `contract.py`, `provenance.py`, `logger.py` (receipts) |
| 5 | Evaluation architecture | Judges, researchers | How are the numbers produced, and can they be reproduced? | Generators, corpora, delivery, agent target arms, sandbox agent, scoring, analyses, reports, CI | `eval/promptfoo/build_suites.py`, `eval/targets/agent_target.py`, `eval/intentseal_eval/*.py`, `.github/workflows/ci.yml` |

**Not shown as built** (planned or out of scope): agent-to-agent message inspection, MCP server vetting, a shared
multi-replica session store (sessions live in one process; storage can be shared), native Bedrock/Vertex SDKs.
