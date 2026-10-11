"""Write the gateway's OpenAPI document and a readable endpoint reference, so the API can be read without running it.

    python scripts/export_openapi.py   ->  docs/api/openapi.json, docs/API.md

Built from the FastAPI app itself (services/gateway/intentseal_gateway/app.py), never by hand. A running gateway
serves the same document at /openapi.json and an interactive version at /docs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# One line for routes whose handler has no docstring (wording checked against the handler in app.py / proxy.py).
DESCRIBE = {
    ("get", "/healthz"): "Liveness: the process is up (open, no key).",
    ("post", "/v1/inspect"): "Inspect content before the model sees it: text or base64 file, source, agent, session. Returns the decision, cleaned content, findings and attack types.",
    ("post", "/v1/actions/check"): "Check a tool call before it runs: tool, arguments, agent, session. Returns the decision, the arguments to run with (pinned fields rewritten), the contract ruling and a notice for the model.",
    ("post", "/v1/outputs/check"): "Check the model's answer before the user sees it: protected values redacted, or the answer withheld.",
    ("post", "/v1/sessions"): "Start a session with the user's task and trusted context; returns the session id and its intent contract.",
    ("get", "/v1/sessions/{session_id}/events"): "Every event of a session in order, with findings, decisions, actions, contract rulings and receipts (replay).",
    ("get", "/v1/decisions"): "Decisions feed, filterable by decision, attack type, agent and time.",
    ("get", "/v1/scorecard/{agent}"): "Latest evaluation reports and summary for an agent.",
    ("get", "/v1/policies/{agent}"): "An agent's policy.",
    ("get", "/v1/costs"): "Security spend across agents: decisions and judge tokens by tier.",
    ("post", "/v1/feedback"): "Reviewer feedback: remember an event or content as a confirmed attack or a false alarm (attack memory).",
    ("get", "/v1/memory"): "Attack memory entries and counts (fingerprints only, never text).",
    ("delete", "/v1/memory/{memory_id}"): "Forget one attack-memory entry.",
    ("get", "/v1/approvals"): "Escalated actions waiting for (or resolved by) a reviewer.",
    ("get", "/v1/sessions/{session_id}/investigations"): "Investigator reports for a session.",
    ("get", "/v1/investigations"): "Recent Investigator reports.",
    ("get", "/demo/scenarios"): "Playground scenarios (generated attacks and benign cases).",
    ("post", "/demo/run"): "Run a Playground scenario on the sandboxed reference agent, protection off or on.",
    ("post", "/proxy/v1/chat/completions"): "LLM proxy, OpenAI format, agent from the key or header.",
    ("post", "/proxy/{agent_id}/v1/chat/completions"): "LLM proxy, OpenAI format: messages and tool results inspected, returned tool calls and answers checked, then forwarded to the agent's provider.",
    ("post", "/proxy/{agent_id}/gemini/v1beta/models/{model_action}"): "LLM proxy, native Gemini format (generateContent, streamGenerateContent).",
    ("get", "/v1/setup/templates"): "Policy templates for registering an agent.",
    ("get", "/v1/providers"): "Configured model providers and whether each has a key.",
    ("get", "/v1/agents"): "Registered agents and their modes.",
    ("post", "/v1/agents"): "Register an agent from a template (starts in monitor mode).",
    ("post", "/v1/agents/{agent}/self-test"): "Self-test an agent's policy with structural probes.",
}


RAW_SPEC = "https://raw.githubusercontent.com/sankalp2515/intentseal/main/docs/api/openapi.json"
WEB = (f"**Browse it on the web, no install:** [interactive reference (Redoc)](https://redocly.github.io/redoc/?url={RAW_SPEC}) · "
       f"[Swagger UI](https://petstore.swagger.io/?url={RAW_SPEC}).")

# Worked example: the three calls an agent makes. Responses were captured from a local gateway (agent `my-assistant`,
# the test pack's generated attack email) and shortened with "…"; the full shapes are in openapi.json.
EXAMPLES = r"""## The three calls an agent makes

The user asked: *"Summarise the partner update email for me. Do not reply to anyone."* The agent then reads an email
that carries a generated attack, and its model proposes a reply. Runnable end to end: `node examples/node-rest/agent.mjs`.

**1. Start a session with the user's task.** IntentSeal compiles the intent contract from the user's own words.

```bash
curl -s http://localhost:8000/v1/sessions -H "Authorization: Bearer local-project-key" -H "Content-Type: application/json" \
  -d '{"agent_id": "my-assistant", "task": "Summarise the partner update email for me. Do not reply to anyone."}'
```

```json
{"session_id": "728d967cc0ea4e00",
 "contract": {"version": 1, "hash": "c833aa5ecd672ebb", "origin": "task",
              "clauses": [{"id": "X13-send", "effect": "prohibit", "capability": "send", "quote": "Do not reply to anyone", "origin": "task"},
                          {"id": "R-send", "effect": "require", "capability": "send", "quote": "policy: 'send' needs the user's explicit request", "origin": "policy"}, …]}}
```

**2. Inspect third-party content before the model sees it.** Hand the model `cleaned_content`, never the original.

```bash
curl -s http://localhost:8000/v1/inspect -H "Authorization: Bearer local-project-key" -H "Content-Type: application/json" \
  -d '{"agent_id": "my-assistant", "session_id": "728d967cc0ea4e00", "source": "email", "filename": "message.eml", "content": "<the email text>"}'
```

```json
{"decision": "BLOCK", "enforced": "BLOCK", "policy_rule": "content-risk-block",
 "reason": "Content risk reached the policy block threshold",
 "cleaned_content": "[Content held by the security policy: content-risk-block]",
 "labels": ["Credential Theft", "Indirect Prompt Injection", "Instruction Override", "Tool Abuse"],
 "risk": 1.0, "tier": 2, "latency_ms": 1134.11, "event_id": "de7f4dfd7ce24d14b7f3", "findings": […]}
```

**3. Check every tool call before it runs.** Run it only when `enforced` is `ALLOW`, with `final_args`; then report a
receipt (`POST /v1/actions/{event_id}/receipt`).

```bash
curl -s http://localhost:8000/v1/actions/check -H "Authorization: Bearer local-project-key" -H "Content-Type: application/json" \
  -d '{"agent_id": "my-assistant", "session_id": "728d967cc0ea4e00", "tool": "send_message", "args": {"to": "partner@vendor.example", "body": "Here is the summary."}}'
```

```json
{"decision": "BLOCK", "enforced": "BLOCK", "final_args": null, "policy_rule": "recipient-not-allowed",
 "contract": {"version": 1, "effect": "prohibit", "capability": "send",
              "clause": {"id": "X13-send", "quote": "Do not reply to anyone", "origin": "task"}},
 "taint": [{"arg": "to", "source": "email", "kind": "target"}],
 "reason": "recipient outside allowed list (1 address(es)); 'to' value appears only in untrusted content, not in the user's request; … the user ruled out 'send' (contract v1, clause X13-send: \"Do not reply to anyone\")",
 "notice": "Action 'send_message' was blocked by the security policy: recipient outside allowed list (1 address(es)). Continue the user's task without it.",
 "latency_ms": 5.52, "event_id": "804f60b0c34e413aa058"}
```

`notice` goes back to the agent's model so it carries on without the call. The Console's Replay shows this session as
an attack-to-action chain (`GET /v1/sessions/{session_id}/provenance`). `local-project-key` is the Docker default and
works only on your machine.
"""


def main() -> None:
    os.environ.setdefault("INTENTSEAL_API_KEYS", "docs:docs-export-only:admin")
    os.environ.setdefault("INTENTSEAL_PUBLIC_KEY", "docs-export-public")
    from intentseal_core.decision_model import StaticDecisionModel
    from intentseal_core.engine import Engine
    from intentseal_core.store import Store
    from intentseal_gateway.app import create_app

    class _NoScore:
        def score(self, text):
            return [0.0 for _ in text] if isinstance(text, list) else 0.0

    app = create_app(engine=Engine(decision_model=StaticDecisionModel(0.0), classifiers=[_NoScore()], store=Store(":memory:")))
    spec = app.openapi()
    out = ROOT / "docs" / "api"
    out.mkdir(parents=True, exist_ok=True)
    (out / "openapi.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False), encoding="utf-8")

    groups: dict[str, list[str]] = {}
    for path, ops in sorted(spec["paths"].items()):
        for method, op in ops.items():
            tag = (op.get("tags") or ["other"])[0]
            summary = (op.get("description") or DESCRIBE.get((method, path)) or op.get("summary") or "").strip().split("\n")[0]
            groups.setdefault(tag, []).append(f"| `{method.upper()}` | `{path}` | {summary} |")
    order = ["engine", "sessions", "evidence", "review", "policy", "proxy", "onboarding", "ops", "demo", "other"]
    lines = ["# API reference", "",
             f"Generated by `python scripts/export_openapi.py` from the gateway app ({spec['info'].get('title', '')} "
             f"{spec['info'].get('version', '')}). The full schema, with every request and response body, is "
             "[api/openapi.json](api/openapi.json); a running gateway serves it interactively at `http://localhost:8000/docs`.", "",
             "**Authentication**: `Authorization: Bearer <key>`. Keys have a scope: *public* (read-only, the Console), *project* "
             "(an application: inspect, check, sessions, proxy) or *admin* (reviewers: approvals, policy, memory). Keys and "
             "organisations: [DEPLOY.md](DEPLOY.md). An application needs the *Engine* and *Sessions* calls; "
             "[INTEGRATION.md](INTEGRATION.md) shows them in context.", "", WEB, "", EXAMPLES, "## Every endpoint", ""]
    for tag in sorted(groups, key=lambda t: order.index(t) if t in order else len(order)):
        lines += [f"### {tag.capitalize()}", "", "| Method | Path | What it does |", "|---|---|---|", *groups[tag], ""]
    (ROOT / "docs" / "API.md").write_text("\n".join(lines), encoding="utf-8")
    print("wrote docs/api/openapi.json and docs/API.md:", sum(len(v) for v in groups.values()), "operations")


if __name__ == "__main__":
    main()
