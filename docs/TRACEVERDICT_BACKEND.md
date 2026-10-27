# TraceVerdict backend handoff

**Updated handoff:** use the [root README](../README.md) for current clean setup, [frontend integration](FRONTEND_INTEGRATION.md) for the browser contract and [release verification](RELEASE_VERIFICATION.md) for actual results. `Dockerfile.backend` now starts the real case-only application, `intentseal_gateway.cases.app:app`. The older sample-install/Docker status below is historical.

TraceVerdict adds a case investigation and repair-validation workflow to IntentSeal. The frontend is intentionally not changed. The application returns graph data, exact policy diffs, job status and hash-bound review artifacts for a future frontend.

## Operating mode and authority

Engineering mode is IMPROVE: reuse the existing action guard, intent compiler, policy models, store and authentication contracts. Models may retrieve evidence and propose explanations or bounded repairs. They cannot execute production tools, approve a candidate or apply a policy. The MVP exports a recommendation; it has no apply endpoint.

## Run the sample

Use Python 3.11 or 3.12. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e packages/core -e packages/sdk -e agents -e services/gateway -e eval
.\.venv\Scripts\python.exe scripts/traceverdict_sample.py
```

The script writes three synthetic reports into `artifacts/traceverdict`; add `--include-world` for complete versioned world-state exports. Rerunning reuses completed case state rather than duplicating repairs. Use a different output directory for a fresh run. The sample uses deterministic templates, a real existing action guard, fresh local sandbox stores and local outbox receipts. It performs no LLM inference and contacts no sponsor endpoint. The short summarize executor returns its input as a deterministic artifact; this is not an evaluated natural-language summarizer.

The implementation was tested with the existing Python environment and explicit source paths pointing to this checkout. A fresh dependency install and a Docker image build are separate release checks; do not assume they passed from those tests.

## Run the sample API for frontend development

Set `INTENTSEAL_API_KEYS` privately using the existing `name:key:scope:org` format. Use separate project and admin keys, with generated random key values. Never put an admin key into browser application code.

```powershell
.\.venv\Scripts\python.exe -m uvicorn intentseal_gateway.cases.sample_app:app --host 127.0.0.1 --port 8000
```

Open `/docs` for schemas. This application exposes only TraceVerdict routes and accepts only synthetic sample cases. It does not expose the legacy inspection and proxy routes with its sample scorer. It needs no sponsor credentials. `Dockerfile.backend` provides the same backend-only sample application; mount persistent storage at `/app/data` if using it. Docker build/run has not yet been verified.

For a live integrated deployment, use the existing gateway startup instructions, set `TRACEVERDICT_NIGHTSHIFT_ONLY=true`, and provide the real Runtime URL, Runtime token and a discovered model route. That profile replaces every legacy model role, including Investigator's fallback role, with Nightshift. Existing direct-provider defaults remain available outside that explicit profile. New TraceVerdict live reasoning always uses its Nightshift adapter, with no silent direct-provider fallback.

`SAMPLE_MODE=true` selects the default for case creation when execution_mode is omitted. An explicit execution_mode is recorded on each case and cannot change later. A live failure never switches a case into sample mode.

## Main API flow

All requests need an authenticated project key unless noted. Case access is limited to the principal's tenant and agent scope; knowing an ID grants no access. The existing gateway's admin scope is the reviewer capability for this MVP.

1. `POST /v1/cases` with `agent_id`, a fixture ID or authorized `session_ids`, `execution_mode`, and an `idempotency_key`.
2. `POST /v1/cases/{id}/investigate` with an idempotency_key. Returns 202 and a job. Poll `GET /v1/cases/{id}/jobs/{job_id}`.
3. Read `GET /v1/cases/{id}` and `/graph`. Follow graph support IDs through `/evidence/{evidence_id}`.
4. Investigation moves through explanation, critic review and at most two revisions. Supported claims lead to at most two proposed repairs. `POST /v1/cases/{id}/repairs` also accepts a supported typed candidate while capacity remains.
5. Start each candidate with `POST /v1/repairs/{repair_id}/validate` and an idempotency key. Poll its job; completed reports also have `GET /v1/validations/{validation_id}`. Case status remains VALIDATING until every proposed candidate has an outcome.
6. An admin reviewer calls `POST /v1/repairs/{repair_id}/approve` with exactly `base_policy_sha256`, `patch_sha256`, and `validation_report_sha256`. Reviewer identity comes from authentication. A rejected/incomplete candidate cannot be approved.
7. `GET /v1/cases/{id}/export` returns the recommendation and results. Approval does not apply the patch.

Example intake:

```json
{"agent_id":"research-agent","fixture_id":"supplier-contact","execution_mode":"sample","idempotency_key":"frontend-example-001"}
```

The other fixture IDs are `invoice-forward` and `report-notify`. Use a distinct intake key for independent cases. Reusing an intake key with different input returns 409.

## Graph contract

Nodes include evidence kind, source locator/version and content hash, or a cited claim with review status. Edges include `basis`, `support_evidence_ids`, and a suggested `style`: observed links are solid, inferred/context links are dashed. Application receipts connect by event ID. Context edges are explicitly not proof that a policy ran or a document caused an action. The export distinguishes withheld, allowed-but-unconfirmed, application-reported-executed and contradiction.

`GET /v1/cases/{id}/history/{version}` returns the hash-checked historical projection, including claims at that point. Revisions do not erase the earlier disputed explanation. Each append observation retains its projection, author/run metadata and parent hash; these hashes detect alteration but do not authenticate a compromised producer.

The future frontend must render attacker-controlled strings as text and respect these labels. There is no new graph database: the graph is a derived projection of case-scoped records. Neither temporal adjacency nor model-generated confidence authenticates a source.

## Persistence and Meterless World Model mapping

`tv_worlds` uses the existing SQLite/PostgreSQL Store abstraction. Each version atomically persists an append observation and the current aggregate through compare-and-swap. The aggregate includes typed evidence entities, tenant/agent/case contexts, source-linked relationships, immutable intake anchors, claims, proposals, jobs and review records.

This is an application implementation of the official World Model Agent Engine reference architecture, not a claimed vendor SDK. Stable IDs, provenance, idempotent ingestion, bounded context selection, a runtime wired/dormant manifest, durable job leases and restart recovery are exercised by feature tests. State is not merely stored: Investigator, critic and repair prompts consume its context builder. Optional vector memory, generalized clustering, automatic maintenance and cross-case enrichment are not implemented.

State writes reject stale versions, invalid transitions, rewritten source evidence and changed intake snapshots. Per-case jobs are serial, process concurrency is two, and the accepted backlog is bounded. Pending jobs survive restart; expired leases are reclaimed. This has SQLite feature-test coverage; PostgreSQL and multi-process failure recovery still need live verification.

## Repair and validation boundaries

Supported paths are `contract.mode`, `contract.out_of_scope`, and an existing send tool's recipient allow-list. Contract mode can only change to enforce. Recipient values must come from a trusted directory. Arbitrary code, paths, tool names, logging changes, reviewer identity and promotion status are not model-controlled patch fields.

Every fixed-action run receives a fresh policy copy, session, local SQLite store, logger and in-memory outbox. The baseline must actually execute the disputed sandbox action. The gate recomputes outcomes from frozen expectations and receipts rather than trusting reported pass labels. It requires all critical scenario IDs and event-linked receipts. Broad recipient restriction fails authorized-send utility; the narrower contract candidate must pass its own checks.

Live validation additionally runs the bounded document agent through Nightshift against baseline and candidate policies, with only local send and deterministic artifact tools. It records model resistance separately from control intervention. A provider failure, model/tool budget exhaustion or timeout leaves validation incomplete. One trial is not a robustness claim. The job deadline is 180 seconds; live trial latency must be measured and the budget revisited if the full suite cannot finish.

The initial fixture template contains one unsafe development action, two frozen unsafe acceptance actions and three utility tasks. Three example cases reuse this template; they are not independent robustness measurements. The larger PRD target of six development attacks, six independently grouped held-out attacks and eight legitimate tasks has not been completed. If acceptance results influence a new repair, retire that acceptance set before evaluating again.

## Sponsor connection and remaining release gates

Set `METERLESS_BASE_URL`, `METERLESS_RUNTIME_TOKEN`, `METERLESS_MODEL`, `ZETARIS_REST_URL`, `ZETARIS_API_KEY`, and `ZETARIS_ORG_ID` privately. The NVIDIA provider key belongs in Nightshift, not the application. Query/model request IDs, requested routes and model evidence returned by the provider are separate fields. A routing alias is not proof of a concrete NVIDIA model.

See `scripts/zetaris/README.md` for registration exports and the governed view contract. Source registration, actual connector/USL DDL, sponsor inference, concrete Nemotron attribution and Zetaris data-quality checks remain pending live access. Read-only HTTP contract tests use mock transports and do not establish sponsor connectivity.

Old sessions without historical policy snapshots or full replay originals can be investigated but cannot produce a validated repair. Their missing inputs are explicit; intake's current policy is not substituted for incident-time policy. The current complete demo path uses server-owned synthetic fixtures with immutable inputs. General historical-session repair remains outside the implemented replay surface.

No automatic apply, rollback service, frontend, demo video or presentation was created in this backend task. No production-readiness claim is made. Preserve the pre-existing-code declaration in `NEW_WORK.md`.
