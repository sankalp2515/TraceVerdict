# Using your own agent and data

The workspace's **Agents** page now exposes reviewer-only agent registration and original incident capture import. Project credentials investigate and validate authorized cases. Reviewer credentials register agents, publish managed evidence and approve recommendations.

## Capture contract

`POST /v1/agents` takes an agent ID and its **current** policy. The policy persists in PostgreSQL and registration preserves existing agents. Organization and credential agent restrictions apply. Registration does not install runtime enforcement into the external agent.

`POST /v1/replay-snapshots` takes the original task, redacted document, historical policy, recipient reference, attempted send and matching execution receipt. Include source locator/version, timezone-aware capture timestamp, original model/tool build references and frozen unsafe/utility scenarios. The first scenario must match the original task/action, and at least one legitimate utility scenario is required.

The strict schema is in `/docs` and docs/traceverdict-openapi.json. [Example capture](../examples/traceverdict/capture/incident.json) and [current policy](../examples/traceverdict/capture/current-policy.json) demonstrate the format. They contain a newly executed **synthetic local sandbox receipt**, not customer telemetry. Substitute your original data and producer references. Preserve uncertainty and redact credentials before upload. Producer attestations remain attestations; the server cannot independently prove source authenticity.

Create a live case using the returned snapshot_id, registered agent_id and a unique idempotency key. The case has no fixture ID. Historical policy and original inputs remain immutable. Raw gateway sessions without historical originals can be investigated with visible gaps but cannot qualify for exact repair validation.

## Evidence ingestion

When the operator enables TRACEVERDICT_MANAGED_SOURCES=true, **Publish to governed sources** copies the capture into this installation's provisioned operational, configuration and reference PostgreSQL databases. Only reviewers can publish. Clients cannot choose database URLs or SQL. Writes retry idempotently. The USL membership join requires all three sources. Publication is not a distributed transaction, so retry a partial dependency failure before investigating.

The live investigator still reads through Zetaris, with no direct-database fallback. For enterprise sources, leave managed publishing disabled and implement an authorized ingestion pipeline against the documented case_evidence view contract. Register connectors/USL through the platform's supported procedures. Automatic discovery of arbitrary enterprise schemas and end-user connector credential provisioning are outside this release.

```powershell
python scripts/traceverdict_import.py incident.json --register-policy current-policy.json --publish --investigate
```

Set TRACEVERDICT_ADMIN_KEY privately. Use --gateway for another installation. Omit --register-policy for an existing agent. The CLI prints safe case/snapshot/job IDs and does not approve or deploy a patch. Continue in the authenticated workspace to inspect evidence, critique, diffs and validation outcomes.

## Supported boundary

Replay supports local send_message outbox execution and deterministic document-read artifacts. The model chooses the action and recipient. The send executor uses a precomputed summary marker, so utility send scenarios use body `summary`. This does not evaluate arbitrary generated prose. Original recorded action bodies can retain historical content. Uploaded code, arbitrary executable plugins, real external sends and automatic production deployment are not supported by the sandbox.

An external agent may use the existing IntentSeal SDK/action guard for enforcement, separately from uploading a TraceVerdict incident. Instrument the application to retain actual receipts and policy/model/build references. For a nonfixture case, the registered current policy must still match the historical base hash before approval. Approved recommendations require a separate controlled rollout.

Operator-managed project/reviewer keys and tenant scopes are supported. Self-service accounts, enterprise SSO and customer-specific secret-vault provisioning are not implemented. Judges can run the reproducible local stack and import supported captures. A public multi-customer SaaS requires additional access provisioning and deployment verification.
