# IntentSeal documentation

| Document | What it covers |
|---|---|
| [INTEGRATION.md](INTEGRATION.md) | Connecting an agent: LLM proxy, Python SDK, REST API, RAG apps; who does what; monitor → enforce |
| [diagrams/](diagrams/README.md) | Five architecture diagrams verified against the code, with their sources |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, data flow, detection tiers, action guard, API, storage |
| [API.md](API.md) | Every REST endpoint, generated from the app; [api/openapi.json](api/openapi.json) |
| [ENGINE.md](ENGINE.md) | Every decision rule: when it fires and what it does |
| [DEPLOY.md](DEPLOY.md) | Docker, Hugging Face Spaces, every setting, checks after deploying, operations |
| [EVALUATION.md](EVALUATION.md) | Measured results: per attack type and channel, false alarms, latency, cost (generated) |
| [ASSURANCE.md](ASSURANCE.md) | What holds when detection fails: intent contracts, paired and repeated runs, red-team loop (generated) |
| [COVERAGE.md](COVERAGE.md) | Nine attack types × every input source, and the F3 · D3 grid (generated) |
| [DECISIONS.md](DECISIONS.md) | Design decisions and their reasons |

Examples: [examples/assistant](../examples/assistant/README.md) (a real tool-calling assistant over your own files,
web pages, email and a knowledge base), [examples/openai_agent](../examples/openai_agent) (protected by the proxy
alone), [examples/langgraph_agent](../examples/langgraph_agent) (protected by the SDK).
