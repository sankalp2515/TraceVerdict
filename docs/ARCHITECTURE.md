# TraceVerdict implemented architecture

[Full-size layered diagram](images/traceverdict-architecture.svg)

The diagram preserves the supplied reference layout while describing the current code. Layers are logical responsibilities, not one container per box. The investigator, critic, repair planner, controller, graph and replay coordinator run in the case API. The frontend, proxy and three source databases have separate containers; Zetaris has its own stack and Nightshift runs separately.

| Diagram layer | Implementation | Important boundary |
| --- | --- | --- |
| Connected agents and analyst | [Frontend](../apps/web), [capture onboarding](../services/gateway/intentseal_gateway/cases/onboarding.py), [integration guide](CUSTOM_INTEGRATIONS.md) | Existing proxy/SDK integration is available from the foundation. New incidents enter through the supported capture contract; arbitrary agent frameworks require mapping their records into that contract. |
| Foundation enforcement and intake | [Action guard](../packages/core), [capture API](../services/gateway/intentseal_gateway/cases/api.py), [publisher](../services/gateway/intentseal_gateway/cases/onboarding.py) | IntentSeal supplies enforcement. TraceVerdict preserves original task/action/receipt and historical snapshots; capture authenticity is operator-attested. Nightshift is used by the new case/replay workflows, rather than automatically by every original runtime request. |
| Investigation data plane | [Zetaris integration](../services/gateway/intentseal_gateway/cases/integrations.py), [USL provisioning](../scripts/zetaris), [evidence repository](../services/gateway/intentseal_gateway/cases/repository.py) | Live investigations read governed templates through Zetaris across three independent PostgreSQL sources. Tenant, agent and case membership scope the records. No model-generated arbitrary SQL. |
| Evidence graph and bounded workflow | [World Model engine](../services/gateway/intentseal_gateway/cases/world_model.py), [state](../services/gateway/intentseal_gateway/cases/world_state.py), [workflow](../services/gateway/intentseal_gateway/cases/service.py) | Stable evidence identities, canonical provenance events and rebuilt context support cited claims. Investigator/critic allow two revisions after the first attempt; unresolved claims end inconclusive. At most two typed repair candidates. Graph relationships are evidence links, not proof of causation. |
| Model service | [Nightshift adapter](../services/gateway/intentseal_gateway/cases/integrations.py), [model-driven replay](../services/gateway/intentseal_gateway/cases/agent_replay.py) | Configured Lightning route supplies investigator/critic/planner reasoning; Ultra supplies replay-agent actions. Returned model IDs, response IDs and usage are retained. Live failures remain visible, with no silent direct-provider or synthetic fallback. |
| Validation and review | [Fixed-action runner and gate](../services/gateway/intentseal_gateway/cases/replay.py), [review service](../services/gateway/intentseal_gateway/cases/service.py) | Fixed-action checks and model-driven local tasks compare baseline and patched policy. Frozen synthetic scenarios test unsafe behavior and legitimate utility. Unsupported tools need adapters. Approval binds exact artifacts and runtime/executor profile; export remains `applied: false`. |

## Evidence graph is a core product component

The graph links incident evidence, cited claims and their supporting records. Content hashes and source versions preserve inspectable provenance. The World Model engine normalizes identities, appends canonical events and rebuilds the context used by the reasoning roles. The frontend lets the reviewer inspect the graph and drill down into original evidence. [World Model implementation and 8/8 upstream conformance results](METERLESS_WORLD_MODEL.md) describe the implemented invariants and limits.

## Execution modes and scope

- **Recorded sample:** account-free frontend using retained JSON; no new sponsor calls.
- **Live investigation:** authenticated intake, managed source publication, governed Zetaris reads and actual Nightshift calls. Case state, jobs and review records persist in the configured PostgreSQL/SQLite store; live Compose uses PostgreSQL.
- **Local replay:** `send_message` writes to an isolated local outbox; artifact reading/summarization is deterministic. It does not send external messages or execute arbitrary customer tools.
- **Review:** an authenticated reviewer approves a recommendation. TraceVerdict does not deploy a production policy.

The diagram's acceptance tasks are frozen synthetic development scenarios, not an independently held-out security benchmark. Provider failures, missing evidence and stale validation artifacts cannot be labeled successful. The [fresh Docker execution](../examples/traceverdict/live/docker-restart/summary.json) and [NVIDIA evidence](NVIDIA_NEMOTRON_EVIDENCE.md) document actual retained outcomes.

## Component provenance

Blue/grey boxes denote integration and source boundaries; orange outlines mark deterministic control. The reused IntentSeal enforcement layer is named explicitly. Green boxes describe TraceVerdict implementation, including its Python implementation of the published Meterless World Model design. [Engineering provenance](NEW_WORK.md) identifies the original baseline and newly added work.

The original runtime design remains available as [foundation architecture](FOUNDATION_ARCHITECTURE.md).
