# TraceVerdict: architecture and release assessment

**Historical assessment before the subsequent implementation. Current closure evidence and remaining release gates are in [RELEASE_VERIFICATION.md](RELEASE_VERIFICATION.md).** Statements below about missing USL, sessions, World Model, indexes and connectivity describe the earlier assessment, not current implementation status.

Assessment date: 27 October 2026. Mode: evaluate the existing implementation. Frontend implementation is excluded.

## Decision

The attached `intentseal-explain-architecture.svg` is a sensible target architecture. The backend implements a substantial, tested synthetic vertical slice of it. **It is not yet production ready or submission ready.** Sponsor authentication now works, but that does not prove the complete product workflow.

The strongest architectural choice is keeping synchronous enforcement separate from asynchronous investigation. Models propose explanations and repairs; code checks permitted changes and test results; an authorized human approves a particular artifact. Preserve that separation.

## Evidence established

| Check | Observed result | What it does not establish |
| --- | --- | --- |
| Zetaris installation | Earlier official verifier passed all nine checks; sample datasets registered | TraceVerdict source federation or a governed case join |
| New Zetaris API token | Authenticated `SELECT 1 AS connectivity_check` returned HTTP 200 and `[["1"]]` | Permissions or correctness of an application evidence view |
| Installed API contract | `/api/v1.0/sql-editor/sqls/run` accepts the implemented request shape; this installation uses numeric organization ID `1` | A hexadecimal organization identifier from a driver log is not interchangeable with the API organization ID |
| TraceVerdict catalog | `SHOW TABLES FROM traceverdict` returned an empty result | No application evidence table/view was demonstrated |
| Nightshift | Authenticated discovery returned 86 routes; live tool calling passed through the TraceVerdict adapter | A complete investigator/critic/planner/replay workflow |
| Model attribution | Runtime response identified `nvidia/nemotron-3.5-lightning-30b-a3b` | Separate provider attribution was absent; do not invent it |
| Current focused regression | 33 passed in 28.29 seconds | Live sponsors are replaced by controlled doubles in these tests |
| Test isolation repair | The Nightshift profile test now isolates environment loading so a private `.env` cannot refill a deliberately deleted setting | No production behavior changed |
| Release-tool checks | Two secret-scanner regression tests passed in 0.21 seconds; changed Python files passed lint; full repository secret scan and Git whitespace check passed | These do not constitute a Git-history or dependency audit |

Private receipts are under `artifacts/traceverdict/`. Private configuration is in the Git-ignored backend `.env`. No credential values belong in reports, videos, agency briefs, or browser bundles.

## Architecture diagram compared with code

| Diagram component | Implementation | Assessment |
| --- | --- | --- |
| Proxy / REST / SDK / execution hooks | Existing foundation in core, gateway, SDK and research agent | Reused foundation; do not count historical results as new-product measurements |
| Synchronous inspection and action guard | Existing deterministic policy and contract checks | Correct authority boundary; complete tool-hook coverage still matters |
| Historical policy/tool/model snapshots | Fixture intake freezes policy/tools and a fixture manifest | Partial. Nonfixture intake records historical-policy and replay-original gaps; model/build references and an incident watermark need a complete capture path |
| Zetaris investigation data plane | Scoped SELECT adapter, evidence parsing and source-export tooling | Contract implemented and basic API query verified. Source registrations, governed joins, quality checks and actual case evidence remain pending |
| Evidence repository and graph | `cases/repository.py`, graph/evidence/history endpoints | Implemented JSON graph. No graph database is required for the MVP. Current edges cover evidence-to-claim support, application receipts and case context; richer copied/causal lineage is not implemented |
| Investigator / critic / repair planner | `cases/service.py`, strict structured tool outputs and bounded revisions | Implemented and mock-tested. Genuine case-level model behavior and failure recovery need retained live runs |
| Meterless World Model | Application-owned `cases/world_state.py`: canonical case state, history, content hashes, context and CAS commits | A meaningful subset, not verified engine conformance; see below |
| Sandbox validation | Fixed-action checks and local-only model-driven trials | Working fixture boundary; arbitrary customer incident replay is unavailable |
| Acceptance and human review | Frozen expectations, exact diffs, report/patch/base hash binding, admin-scoped approval | Implemented recommendation gate. Approval does not deploy a patch |
| Frontend workspace | JSON contracts and sample API exist | New case workspace, graph rendering and review UX are deferred |

### The graph is a core feature

The graph connects records, claims and application outcomes so an analyst can inspect why a conclusion was reached. It is central to the explanation experience, alongside the critic and tested repair comparison. It is not a visualization of an unrestricted model reasoning trace. Observed evidence, inferred influence and temporal context must remain distinguishable. A cited source does not automatically prove a causal claim.

### What Meterless actually requires

The [official World Model documentation](https://github.com/Meterless/Meterless/tree/main/engines/world-model) distributes an implementation specification and an executable reference, rather than requiring a particular production SDK. Implementing the architecture in Python is legitimate. Installing an unused package would not close this gap.

The current subset has stable case-scoped evidence IDs, durable state, provenance fields, version checks and historical projections. Still needed: a precise mapping to the specification, input normalization/deduplication semantics, rebuilding projections from canonical observations, complete context budgets and the applicable feature/conformance evidence. Re-ingesting the same evidence deduplicates entity keys, but `ingest_records` still commits another history entry; establish the intended exactly-once observation semantics explicitly.

The [published conformance adapter](https://github.com/Meterless/Meterless/blob/main/engines/world-model/conformance/README.md) expects a module exporting `WorldModel`, `entityIdFromName`, `normalizeName`, and `decide`. No adapter or green run against our implementation is present. A bridge or faithful equivalent must exercise our actual state implementation; running only the vendor reference suite would not prove our feature works.

## Submission blockers beyond frontend, in order

1. **Complete the actual Zetaris evidence layer.** Register operational records, independently maintained historical configuration and trusted reference sources. Retain connector definitions, source versions, exploratory queries, governed semantic-view DDL, case-scoped join output and a data-quality execution. The backend expects `traceverdict.case_evidence` unless explicitly configured otherwise. Three exported groups do not automatically mean three independent data sources.
2. **Prove one complete live case.** Use real Zetaris retrieval and Nightshift for investigator, critic and repair roles. Retain query receipts, source IDs, model IDs, structured outputs, critique/revision and terminal result. Failures must stay incomplete, without switching into sample mode.
3. **Close Meterless Engine proof.** Map and implement the relevant World Model contract, run reproducible feature tests and the applicable conformance path against our implementation, and show how the feature uses that state.
4. **Prove both repair effectiveness and retained utility.** Run fixed-action and actual model-driven baseline/candidate trials separately. Show a disruptive repair rejected and a supported alternative tested. Current examples reuse one six-scenario template. The PRD target is three incidents, six unsafe development cases, six independently grouped unsafe held-out cases and eight legitimate tasks; the current examples do not meet that target. Record errors, resisted attacks and unknown outcomes separately.
5. **Resolve the real-incident replay boundary.** `create()` marks nonfixture cases as lacking historical policy and complete replay inputs; `plan()` stops on these gaps, and `validate()` requires a fixture. Either implement immutable real intake/replay capture or submit a clearly scoped synthetic sandbox product. Do not represent it as a general incident repair service.
6. **Verify release reproducibility.** Clean environment installation, backend container build, PostgreSQL case-state behavior, restart recovery and a repeated live demo must pass. `Dockerfile.backend` currently starts the sample-only API. It is not a verified deployment of the complete live product. Current private endpoint URLs are for the Windows-host process; a backend container needs reachable service addresses instead of assuming its own `localhost` is the Windows host. Configure the Zetaris service/network and a reachable Nightshift runtime address, then test that deployed topology.
7. **Finish the submission package.** Public repository, usable clean-clone README, three labeled examples, sanitized trace evidence, 1–4 minute demo, slide deck, sponsor/Engine explanation, selected track and accurate team details. Verify links as an unauthenticated reviewer. Declare pre-existing product code as the supplied rules require, even when the team owns it; confirm track eligibility if unclear.

The supplied rules set the deadline at **27 October 2026, 23:45 UTC / 28 October, 05:15 IST**. A proposed improvement is not a passed release check.

## Production gaps and a practical scaling path

| Finding grounded in current code | Consequence | Next production step |
| --- | --- | --- |
| `WorldState.commit()` rewrites a JSON aggregate containing current state and growing historical projections | Write amplification and increasingly expensive hashing as cases grow | Separate append-only observations, indexed projections, jobs and large artifacts; add retention and schema migrations |
| `WorldState.pending()` scans/deserializes all case bodies every recovery interval; repair/report lookup scans visible case bodies | Work grows with historical case count | Indexed job status/lease queries and direct tenant-scoped repair/report lookup, plus pagination |
| `asyncio.Semaphore(2)` is per process; backlog admission is a scan rather than transactional global admission | Adding API workers changes concurrency and can oversubscribe providers | Explicit durable worker ownership, global quotas/backpressure and measured worker limits; a PostgreSQL-backed queue is sufficient initially |
| Leases and CAS exist, but no real multi-process kill/restart test was executed | Crash recovery and concurrent completion remain insufficiently evidenced | Two-worker lease contention, process kill during each stage, expired lease retry and duplicate-result tests |
| PostgreSQL store uses one locked connection per instance | PostgreSQL alone does not establish high throughput | Connection pooling when measured demand requires it; transaction boundaries and isolation tests |
| Context budget counts entity characters, but not the complete claims/relationships/message envelope | Large graphs can exceed model context even when the entity limit passes | Budget the full serialized context; prioritize required evidence, and mark unsupported/truncated conclusions incomplete |
| Historical/model/build capture is incomplete outside fixtures | Replay and approval applicability cannot be established for arbitrary incidents | Immutable artifact storage, capture timestamp/active interval, model/tool/build references and snapshot watermark |
| Gateway has key scopes, request limits, CORS and basic operational endpoints | Useful controls already exist, but they do not establish enterprise identity or workflow SLOs | Session-based UI access, least-privilege reviewer roles, secret rotation, TLS and measured workflow-level metrics |
| Existing readiness checks cover foundation dependencies, not the whole new case integration | A healthy process can lack a usable governed view or working sponsor feature | Case-specific dependency readiness, provider/data-layer latency, queue age, incomplete reasons, cost and retry metrics |
| Sandbox tools are hardcoded local outbox/artifact executors | Appropriate for this bounded MVP; not a hardened arbitrary-code sandbox | Preserve the allowlist; require separate process/container isolation and egress controls before supporting arbitrary tools |
| Hashes detect changes but do not authenticate a compromised evidence producer | Integrity claims can be overstated | Trusted ingestion identity, access controls, audit retention and optional signed producer receipts based on deployment needs |

Start with one API service, bounded worker capacity, PostgreSQL, restricted artifact storage, Zetaris and Nightshift. Establish p50/p95 latency, throughput, failure rate, queue age and cost under a declared workload before adding replicas. Reuse existing health/auth/metrics controls; extend them for cases. Kubernetes, a separate graph database and a vector database are not prerequisites for this product's first reliable deployment.

Production release also needs restore-tested backups, retention/deletion policy, dependency/container review, incident procedures and a controlled deployment/rollback procedure. These are separate from the MVP's recommendation export. No scalability benchmark or production certification is claimed by this review.

The release scan initially flagged public model IDs because it treated every sufficiently long `.env` value as a credential. The scanner now exempts only the known `METERLESS_MODEL` metadata field when its value has a recognized Meterless/NVIDIA route shape. Other environment values and vendor-key patterns remain checked. Tests demonstrate that opaque runtime tokens and key-shaped values still block publication and are not printed.

## Recommended next build order

Governed Zetaris view → one genuine live case → World Model proof → complete safety/utility replay evidence → reproducible install and recovery checks → integrated frontend/demo → submission assets. Make the smallest truthful end-to-end workflow reliable before expanding scope.

Sources: supplied PRD and implementation guide; supplied architecture SVG; supplied submission requirements and official rules; actual repository code and executed checks; the linked official Meterless documentation. Historical test results in `TRACEVERDICT_VALIDATION.md` remain historical, not current live workflow proof.
