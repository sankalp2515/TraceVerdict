# Putting IntentSeal into an existing agent system

Who does what, in order. Nothing here requires changing the agent's model provider or rewriting the agent.

## 1. Where IntentSeal sits

```
                  user ──► your agent ──► model provider (OpenAI, Anthropic, Gemini, Groq, Azure, local …)
                               │   ▲
         reads web/files/email │   │ tool calls (send, write, fetch, query …)
                               ▼   │
                    ┌──────── IntentSeal gateway ────────┐
                    │ inspect what the agent reads       │──► decision log ─► Console, SIEM, replay
                    │ check every action before it runs  │
                    └────────────────────────────────────┘
```

One gateway (a container, `docs/DEPLOY.md`) serves any number of agents. Each agent has a policy; each team can be its
own organisation with its own keys (D-043).

## 2. Three ways to connect an agent

| Path | Change to the agent | Protects | Best for |
|---|---|---|---|
| **LLM proxy** | Base URL (and key) of the model client | Every user message and tool result before the model sees it; every tool call the model returns, before the agent runs it | Any language and framework that uses an OpenAI-compatible client or the Anthropic SDK |
| **Python SDK** (`intentseal`) | About 5 lines: a session, `guard.inspect(...)` on content, `@guard.tool()` on tools | The same, plus content the agent reads outside model messages (files, pages, emails) at the moment it reads them, and trusted context (pinned fields) | Python agents; any model provider; embedded or against the gateway |
| **REST API** | Calls to `/v1/inspect` and `/v1/actions/check` from your hooks | Whatever you route through it | Other languages, or frameworks with their own middleware |

### Provider compatibility (proxy)

| The agent uses | Point it at | Notes |
|---|---|---|
| OpenAI SDK, or any OpenAI-compatible client (LangChain `ChatOpenAI`, LlamaIndex, CrewAI, AutoGen, Vercel AI SDK, …) | `OPENAI_BASE_URL=<gateway>/proxy/<agent>/v1` | Streaming supported. The policy's `upstream` decides the real provider |
| Anthropic SDK (Claude) | `ANTHROPIC_BASE_URL=<gateway>/proxy/<agent>/anthropic` | Native pass-through to Anthropic keeps thinking, documents, cache control; streaming supported |
| Google Gen AI SDK (Gemini) | `genai.Client(api_key=<IntentSeal key>, http_options={"base_url": "<gateway>/proxy/<agent>/gemini"})` | Native `generateContent` and `streamGenerateContent`; upstream must be `gemini`. Or use Gemini's OpenAI-compatible endpoint through the OpenAI path |
| Groq, Mistral, OpenRouter, NVIDIA, DeepSeek, xAI, Together | OpenAI path (upstream = that provider) | |
| Azure OpenAI | OpenAI path (upstream `azure_openai`, set the resource URL in `config/providers.yaml`) | `api-key` header handled |
| Local models (Ollama, vLLM, LM Studio, llama.cpp server) | OpenAI path (upstream `ollama`, or any `no_auth` OpenAI-compatible entry) | No key needed |
| AWS Bedrock, Vertex AI native SDKs | SDK or REST path | Not proxied natively yet |

The **SDK and REST paths are provider-agnostic**: they inspect content and check tools, never the model call, so they
work with any model, including ones not listed.

### Whose provider key

Per agent, in its policy (`upstream.key`):
- `gateway`: the gateway holds the provider key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, … in its environment). The
  agent only has an IntentSeal project key.
- `client`: the agent keeps its own provider key and sends it in the `X-Upstream-Key` header. The gateway forwards it
  and never stores it (it is redacted from logs).

### RAG applications

Retrieved documents are third-party content, whatever message they are placed in.
- **Proxy**: wrap each retrieved chunk in `<document>…</document>` (inside `<context>…</context>`; also recognised:
  `<documents>`, `<search_results>`, `<retrieved>`, `<retrieved_context>`, `<knowledge>`; configurable with
  `INTENTSEAL_PROXY_CONTEXT_TAGS`) in the system or the user message. Tagged text is inspected as untrusted `rag` content
  and cleaned in place; the operator's prompt outside the tags stays trusted and the user's own words are checked
  first and stay the user's (D-050). Untagged context pasted into the user message is judged as the user's words, with
  the weaker user-turn checks; untagged context in the system prompt is not inspected.
- **SDK**: check each file when it is **indexed** (`guard.inspect_result(data, source="rag", filename=...)`; keep
  BLOCK/ESCALATE files out, index `cleaned_content`) and each chunk when it is **retrieved**
  (`guard.inspect(chunk, source="rag")` inside the user's session).
- Inline images and PDFs in user messages (`data:` URLs, Anthropic `image` / `document` blocks) are extracted and
  OCR-inspected by the proxy; remote image URLs are fetched by the provider, not by the gateway.
- Console → Set up has a **Knowledge assistant (RAG)** template and a **RAG app** connect tab.
  `examples/assistant` is a complete, runnable example (SDK path, or proxy with `ASSISTANT_CONNECT=proxy`).

## 3. Step by step

| # | Who | What | Where |
|---|---|---|---|
| 1 | Platform / DevOps | Deploy the gateway, set provider keys and IntentSeal keys | `docs/DEPLOY.md` |
| 2 | Security lead | Register the agent from a template (research assistant, customer support, coding agent, blank); choose upstream provider and key mode. Starts in **monitor** mode | Console → **Set up**, or `POST /v1/agents` |
| 3 | Developer | Connect the agent: copy the snippet for its stack (proxy env vars, OpenAI or Anthropic SDK, IntentSeal SDK, REST) | Console → Set up → 3, or `GET /v1/agents/<agent>/connect` |
| 4 | Developer | Run the self-test: three harmless probes prove the checkpoints fire on this agent's real policy | Console → Set up → 4, or `POST /v1/agents/<agent>/self-test` |
| 5 | Security lead | Use the agent normally for a while. In monitor mode every decision is recorded, nothing is blocked. Watch for `tool-not-allowed` (rename or add tools), `action-not-requested`, false alarms (mark them; they are remembered) | Console → Decisions, Review |
| 6 | Security lead | Tighten the policy: allow-lists (recipients, domains), pinned fields, intent terms, thresholds | Console → Policy, or `PUT /v1/policies/<agent>` |
| 7 | Security lead | Switch to **enforce** | Console → Policy |
| 8 | Security / SOC | Send decisions to the SIEM; review escalations; replay incidents | `INTENTSEAL_SIEM_SINKS` or `/v1/export/decisions`; Console → Review, Replay |
| 9 | Product manager | Track caught attacks by type, false alarms, cost per agent | Console → Overview, Results |

## 4. Examples

Proxy, OpenAI SDK (Python), gateway holds the provider key:

```python
from openai import OpenAI
client = OpenAI(base_url="https://<gateway>/proxy/support-bot/v1", api_key=INTENTSEAL_PROJECT_KEY)
reply = client.chat.completions.create(model="gpt-5.1", messages=messages, tools=tools)
```

Proxy, Anthropic SDK, the agent keeps its own key:

```python
import anthropic
client = anthropic.Anthropic(base_url="https://<gateway>/proxy/support-bot/anthropic", api_key=INTENTSEAL_PROJECT_KEY,
                             default_headers={"X-Upstream-Key": ANTHROPIC_API_KEY})
msg = client.messages.create(model="claude-opus-5-5", max_tokens=4096, messages=messages, tools=tools)
```

Policy fragment for that agent:

```yaml
agent: support-bot
mode: monitor
upstream: { provider: anthropic, key: client }      # model: unset = the model the agent asks for
tools:
  lookup_customer: { risk: medium, failure: closed, pinned: [customer_id] }
  issue_refund:    { risk: high, failure: closed, pinned: [customer_id], escalate_if_uncertain: true,
                     intent_terms: [refund, money, reimburse, return] }
```

SDK (any provider), deepest protection:

```python
from intentseal import Guard
guard = Guard("support-bot", remote="https://<gateway>", api_key=INTENTSEAL_PROJECT_KEY)
with guard.session(user_id=user.id, task=user_message, trusted={"customer_id": user.customer_id}):
    page = guard.inspect(html, source="web")      # cleaned content, or a safe notice
    ...

@guard.tool()
def issue_refund(customer_id: str, amount: float): ...
```

### Connect an existing agent (Hermes Agent)

Any agent that lets you set a custom OpenAI-compatible endpoint can be protected without touching its code. Example:
[Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research, MIT), a personal agent with 40+ tools
(files, terminal, web, browser, memory). With the gateway running (README, Quick start, Option 1), which ships a policy
for it (`policies/hermes.yaml`, enforce mode, the acting tools checked):

1. Install Hermes from its official repository only (Windows PowerShell: `iex (irm https://hermes-agent.nousresearch.com/install.ps1)`;
   Linux, macOS, WSL2: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`).
2. Point it at IntentSeal: `hermes model` → **Custom endpoint**, base URL `http://localhost:8000/proxy/hermes/v1`,
   API key `local-project-key` (your IntentSeal project key), model `intentseal-default`, context length `128000`.
   Or in Hermes' `config.yaml`:

   ```yaml
   model:
     provider: custom
     base_url: http://localhost:8000/proxy/hermes/v1
     api_key: local-project-key
     default: intentseal-default
     context_length: 128000
   ```
3. Run `hermes` and work as usual.

Which model answers: the policy sets no `upstream`, so Hermes' calls go to the gateway's own model chain (Groq, then
Gemini, then NVIDIA, with the keys in the gateway's `.env`), which fails over when a free tier is busy. To pin a model,
set `upstream: { provider: gemini, model: <model> }` (or any provider in `config/providers.yaml`) in the Console
(Policy) or in `policies/hermes.yaml`.

What is checked: every file, page, command output and search result Hermes receives comes back as a tool result and
is inspected before the model sees it; `terminal`, `execute_code`, `write_file`, `patch` and `send_message` calls are
checked before Hermes runs them; the answer is checked for protected data. Each decision appears in the Console under
the agent `hermes`.

## 5. What changes for the agent

- Clean content: unchanged. Content with an instruction aimed at the model: the instruction is quarantined in place
  (the rest is kept), or the content is withheld with a short notice.
- Allowed tool calls: unchanged (pinned fields are set from the signed-in user). Blocked calls: the agent gets a notice
  ("Action … was blocked …. Continue the user's task without it.") instead of the call. Escalated calls: "awaiting
  approval"; a reviewer can approve that exact call once.
- Latency: the fast path adds about 0.1–1 s; documents that go to the AI judge add seconds (see docs/EVALUATION.md).
