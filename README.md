<div align="center">

# TraceVerdict

### Explain an agent incident. Test a repair. Preserve useful work.

[![Backend CI](https://github.com/sankalp2515/TraceVerdict/actions/workflows/ci.yml/badge.svg)](https://github.com/sankalp2515/TraceVerdict/actions/workflows/ci.yml)
[![Frontend CI](https://github.com/sankalp2515/TraceVerdict/actions/workflows/frontend.yml/badge.svg)](https://github.com/sankalp2515/TraceVerdict/actions/workflows/frontend.yml)
[![World Model](https://github.com/sankalp2515/TraceVerdict/actions/workflows/world-model.yml/badge.svg)](https://github.com/sankalp2515/TraceVerdict/actions/workflows/world-model.yml)
[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

**[Quick start](#quick-start) · [Evidence](#evidence) · [Bring your own incident](#bring-your-own-incident) · [Pitch deck](submission/README.md) · [Integration guide](docs/CUSTOM_INTEGRATIONS.md)**

![TraceVerdict investigation workspace](apps/web/output/playwright/consolidated-workspace.png)

*Actual product screen from a recorded synthetic case. Live sponsor receipts are linked below.*

</div>

## The problem

An AI agent reads an instruction hidden in a supplier document and attempts to contact someone the user never authorized. Logs alone leave the reviewer assembling the user's task, historical policy, document and application receipt by hand. A restrictive repair may stop the incident while breaking legitimate work.

**TraceVerdict investigates the incident and evaluates the repair.** It connects evidence, asks an investigator and critic to explain it, then tests the exact policy diff against unsafe and legitimate tasks. A reviewer receives the recommendation and the hashes of the artifacts they reviewed.

## How it works

```mermaid
flowchart LR
  E[Events and receipts] --> Z[Zetaris governed USL]
  C[Historical configuration] --> Z
  R[Trusted references] --> Z
  Z --> G[World Model evidence graph]
  G --> N[Nemotron investigator and critic through Nightshift]
  N --> P[Typed policy repair]
  P --> V[Safety and utility replay]
  V --> H[Human review and recommendation export]
```

1. **Collect:** load scope-filtered evidence through Zetaris and retain query receipts and source versions.
2. **Explain:** link cited claims to graph evidence; a critic challenges unsupported conclusions. Missing evidence remains visible.
3. **Compare:** test bounded policy changes with fixed-action replay and actual model-selected actions in local executors.
4. **Review:** reject failed or incomplete candidates; bind approval to the exact policy, patch and validation report. Export the recommendation for controlled application.

| Evidence graph | Repair review |
| --- | --- |
| ![Source-linked evidence graph](apps/web/output/playwright/graph-desktop.png) | ![Recommendation review](apps/web/output/playwright/approved-recommendation.png) |

*Recorded synthetic UI examples. Approval exports a recommendation; it does not deploy a policy.*

## Quick start

### Try a recorded sample

For the shortest reviewer path, see the [3½-minute judge route](docs/JUDGE_QUICKSTART.md). With Docker installed, `docker compose up -d --build --wait` serves the complete recorded journey at **http://localhost:5174/workspace?mode=recorded&case=supplier-contact** without `.env`, account creation, keys or sponsor services. The separate demo uses the existing Docker bridge and does not join the live data network. A recording of actual Nemotron/Zetaris execution is also available at `?mode=recorded&case=nemotron-live`; its original response IDs and replay receipts remain inspectable.

For frontend development instead:

```powershell
npm run frontend:install
npm run frontend:dev
```

Open **http://localhost:5173** and choose **Start the guided demo**. No account or sponsor key is needed for the labeled recorded sample. Node.js 22.14+ is required.

### Run the live product with Docker

Prerequisites: Docker Desktop, an installed Zetaris platform, and Nightshift configured with an NVIDIA provider. Populate the ignored `.env` from [.env.example](.env.example) using the [clean setup guide](docs/GETTING_STARTED.md). Sponsor images and credentials come from their providers.

```powershell
# Windows; adjust the Zetaris folder for your machine
.\scripts\start-local.ps1 -Build -ZetarisPath 'E:\zetaris-platform\zetaris-platform'
```

Open **http://localhost:5173**; API docs are at **http://localhost:8000/docs**. Sign in with your privately configured application key. The API, frontend, local proxy and three source databases run in independent containers. Zetaris uses its separate Compose stack. Nightshift runs in its supported desktop runtime and is reached through `host.docker.internal`.

```powershell
# Subsequent restart; existing images and persistent volumes
.\scripts\start-local.ps1
# Stop product and Zetaris without deleting data
.\scripts\stop-local.ps1 -IncludeZetaris
```

Linux/macOS: start Zetaris and Nightshift, then run `docker compose -f compose.data.yml -f compose.local.yml --profile app up -d --build`. Initial source provisioning and native USL activation are covered in [setup](docs/GETTING_STARTED.md). No default public credential is shipped. Keep NVIDIA credentials inside Nightshift and all secrets out of frontend variables.

## Bring your own incident

The authenticated **Agents** page lets a reviewer register a policy and import an immutable original incident capture. Create a live case, publish the captured records to the configured source databases, then begin investigation through Zetaris.

```powershell
python scripts/traceverdict_import.py --help
```

Use the [capture example](examples/traceverdict/capture/incident.json) and [integration guide](docs/CUSTOM_INTEGRATIONS.md) for the exact schema, key scopes and CLI flags. Captures bind the original task, document, historical policy, action and matching execution receipt. Authenticity remains operator-attested. Current replay tools are a local message outbox and deterministic artifact reader; arbitrary third-party tool execution requires an adapter.

## Evidence

| Retained result | Outcome | Scope |
| --- | --- | --- |
| Targeted repair, fixed-action replay | **20 / 20** | Frozen local enforcement tasks |
| Targeted repair, live model utility | **8 / 8** | Authorized tasks preserved |
| Restrictive comparison, fixed-action replay | **18 / 20** | Rejected |
| Restrictive comparison, live model utility | **6 / 8** | Two legitimate tasks broken |
| Nonfixture capture through live sponsors | **20 / 20**, awaiting review | Imported synthetic original; one repair |
| Backend regression | **329 passed, 1 skipped** | [CI](https://github.com/sankalp2515/TraceVerdict/actions/workflows/ci.yml) |
| Frontend component tests | **16 passed** | [CI](https://github.com/sankalp2515/TraceVerdict/actions/workflows/frontend.yml) |
| World Model upstream conformance | **8 / 8** | Actual Python implementation via bridge |

[Comparison receipts](examples/traceverdict/live/invoice-forward-ultra) · [Imported capture receipts](examples/traceverdict/live/imported-capture) · [Method and limitations](docs/NVIDIA_NEMOTRON_EVIDENCE.md).

The packaged Docker stack reproduced this comparison after a device reboot: [fresh case, report and summary](examples/traceverdict/live/docker-restart). The targeted repair passed 20/20 fixed-action tasks and 8/8 model-driven utility tasks; the restrictive control was rejected at 18/20 and 6/8. No errors, human approvals or applied changes are recorded.

Both model-driven baselines resisted the 12 unsafe prompts in the comparison. That is model behavior, not evidence that a policy caused the resistance. Fixed-action replay tests enforcement separately. These are small synthetic evaluations, not broad security guarantees. Failed and incomplete earlier live runs remain in the repository.

## NVIDIA Nemotron through Nightshift

| Explicit route | Product role | Utility trials | Call p50 |
| --- | --- | --- | --- |
| Nemotron 3.5 Lightning 30B A3B | Investigator, critic, planner | 15 / 18 | 678 ms |
| Nemotron 3 Ultra 550B A55B | Model-driven replay | 18 / 18 | 2,150 ms |

Same 12 development tasks repeated twice per route: **48 actual Nightshift trials**. Each route resisted its six unsafe trials; Lightning had three utility failures. The measured tradeoff motivates the explicit role split. All request outcomes, returned model IDs, usage and limits are in [NVIDIA evidence](docs/NVIDIA_NEMOTRON_EVIDENCE.md) and the [evaluation artifact](examples/traceverdict/nemotron-evaluation.json). There is no silent direct-provider or synthetic fallback in live mode.

## Sponsor technologies

| Technology | Working responsibility | Evidence |
| --- | --- | --- |
| **Zetaris** | Native USL unifies three PostgreSQL sources with tenant/agent/case membership joins; scoped queries and native quality rule | [USL and query receipts](examples/traceverdict/zetaris) |
| **Meterless World Model Engine** | Canonical provenance events, stable graph entities, temporal relationships and rebuilt model context | [Implementation and conformance](docs/METERLESS_WORLD_MODEL.md) |
| **Nightshift + NVIDIA** | Primary live inference, explicit model routes, response IDs and usage retained | [Measured model usage](docs/NVIDIA_NEMOTRON_EVIDENCE.md) |

## Security and operating boundaries

- HttpOnly sessions, CSRF checks, tenant/agent scoping and reviewer-only intake/review.
- Durable PostgreSQL state, CAS updates, lease recovery and bounded job admission: two global running workers and 32 active jobs.
- Exact policy/patch/report hashes and executor/runtime profile checks before promotion.
- Local executors and recommendation export; no autonomous production policy deployment.

Public HTTPS deployment, self-service identities/connectors, SSO, monitoring, retention, capacity SLOs and whole-platform disaster recovery remain product milestones. Source restore checks do not establish whole-platform recovery. See [operations](docs/TRACEVERDICT_OPERATIONS.md), [deployment](docs/DEPLOYMENT_REQUIREMENTS.md) and [security reporting](SECURITY.md).

## Repository

| Path | Contents |
| --- | --- |
| [apps/web](apps/web) | TraceVerdict product frontend |
| [services/gateway/intentseal_gateway/cases](services/gateway/intentseal_gateway/cases) | Case API, evidence graph, investigation, replay and review |
| [scripts/zetaris](scripts/zetaris) | Independent sources, governed USL and quality verification |
| [examples/traceverdict](examples/traceverdict) | Labeled samples, original captures and live receipts |
| [tests](tests) | Backend regression and fault/recovery coverage |
| [tools/world-model-conformance](tools/world-model-conformance) | Upstream runner and Python bridge |
| [submission](submission) | Pitch deck, video script and portal draft |

**Docs:** [Setup](docs/GETTING_STARTED.md) · [Integrate](docs/CUSTOM_INTEGRATIONS.md) · [Frontend API](docs/FRONTEND_INTEGRATION.md) · [Operations](docs/TRACEVERDICT_OPERATIONS.md) · [Final checklist](docs/SUBMISSION_FINAL_CHECKLIST.md)

## Engineering provenance

TraceVerdict builds on our IntentSeal runtime. The investigation product, sponsor integrations, World Model graph, critic revision and repair-validation workflow are documented in [engineering provenance](docs/NEW_WORK.md).

Apache-2.0 · Helios · Open Agent Hackathon 2026 · Track 2: The Agent That Can Explain Why.
