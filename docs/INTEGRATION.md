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
| Google Gemini | Gemini's OpenAI-compatible endpoint through the OpenAI path (upstream `gemini`) | Native `generateContent` clients: use the SDK or REST path |
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

## 5. What changes for the agent

- Clean content: unchanged. Content with an instruction aimed at the model: the instruction is quarantined in place
  (the rest is kept), or the content is withheld with a short notice.
- Allowed tool calls: unchanged (pinned fields are set from the signed-in user). Blocked calls: the agent gets a notice
  ("Action … was blocked …. Continue the user's task without it.") instead of the call. Escalated calls: "awaiting
  approval"; a reviewer can approve that exact call once.
- Latency: the fast path adds about 0.1–1 s; documents that go to the AI judge add seconds (see docs/EVALUATION.md).
