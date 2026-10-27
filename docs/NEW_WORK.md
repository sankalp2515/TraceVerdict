# TraceVerdict engineering provenance

TraceVerdict is the Helios team's Track 2 product for investigating unauthorized agent actions and validating bounded repairs. Track 2 eligibility was confirmed by the team on 28 October 2026.

## Components and lineage

The runtime action guard, intent compiler, policy models, SDK and foundational gateway come from the team's IntentSeal codebase. The separate TraceVerdict checkout started from commit `afad26ac673a7adf94a78a0ea94e9c87f0bdc7b1`; the original checkout was not modified. Existing licenses and attribution remain in place.

## TraceVerdict implementation

- Case investigation API, strict evidence/claim/repair contracts and source-linked graph.
- Native Zetaris USL over three independent PostgreSQL sources, scoped SQL templates and data-quality checks.
- Python implementation of the Meterless World Model Engine with an unchanged upstream conformance runner and bridge.
- Nightshift as primary AI runtime: NVIDIA Nemotron Lightning investigator/critic/planner and explicit Ultra model-driven replay.
- Evidence-first critic revision, visible uncertainty, immutable original captures and runtime/executor fingerprints.
- Fixed-action and model-driven safety/utility replay, exact policy diffs, hash-bound human review and recommendation export.
- Durable PostgreSQL/SQLite state, CAS, leases, job admission/recovery, sessions/CSRF, tenant/agent scope and scoped operational queue signals.
- Product frontend, guided no-account sample, recorded live Nemotron evidence, source inspection, original-incident intake and independent demo/live Docker configurations.

## Evidence and limits

[Current release verification](RELEASE_FOLLOWUP_2026-10-28.md), [NVIDIA measurements](NVIDIA_NEMOTRON_EVIDENCE.md), [Engine conformance](METERLESS_WORLD_MODEL.md), [fresh Docker case](../examples/traceverdict/live/docker-restart/summary.json) and [judge quickstart](JUDGE_QUICKSTART.md) contain the executed results and operating boundaries.

Published incidents are synthetic; sponsor calls and local application receipts are real. Recordings run no new inference. Original captures are operator-attested. The supported replay executors are a local message outbox and deterministic artifact reader. Approval exports a recommendation and does not deploy production policy.
