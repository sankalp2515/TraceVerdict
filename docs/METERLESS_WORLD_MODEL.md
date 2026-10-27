# Meterless World Model implementation and proof

The product implements the Meterless World Model specification in Python at `services/gateway/intentseal_gateway/cases/world_model.py`. It is application code derived from the published architecture, not a claim that Meterless distributes a required Python SDK.

Upstream specification/conformance source: https://github.com/Meterless/Meterless/tree/main/engines/world-model

Retrieved upstream HEAD: `1742dec56a66e58eef9dda2d2b865823758ca8cd` (verify against the recorded checkout when updating). The unchanged upstream conformance runner is included under `tools/world-model-conformance/runner.ts` with its Apache-2.0 license. The bridge invokes the same Python class used by the application; it does not substitute the upstream reference implementation.

## Working product feature

Real Zetaris evidence enters `CaseService.ingest_records()`. The engine validates provenance, resolves stable external identities and appends content-hashed canonical events. Re-ingesting identical evidence produces no new engine events. The case transaction durably stores the engine event stream under compare-and-swap version control. Investigator, critic and repair contexts read evidence through the engine's rebuilt projection. Evidence payloads and canonical event prefixes cannot be silently rewritten.

Context budgets now include the complete claim/relationship envelope, rather than only counting entity payloads. Large evidence can be omitted with an explicit truncation signal; required context exceeding the budget fails instead of claiming completeness. Original evidence remains accessible through authorized drilldown endpoints.

Case persistence schema 2 keeps full historical projections in an indexed history table and compact manifests in the current case aggregate. Earlier schema-1 cases remain readable. Jobs and repair/report lookups have transactional indexes; a shared scheduler bounds active workers and admission across connections.

## Official conformance

Executed against our Python implementation: **8/8 passed**.

Covered upstream invariants: normalized stable identity, identity separation, merge-band boundaries, mandatory provenance, duplicate-ingest idempotency, genuine changes producing a different canonical state, temporal relationship validity, and ordered audit mutations.

Reproduce after installing the Python application and Node.js:

```powershell
Set-Location tools/world-model-conformance
npm ci
$env:WORLD_MODEL_IMPL = "$PWD/adapter.ts"
$env:WORLD_MODEL_PYTHON = 'python'
npm test
```

Use an installed Python executable with the application dependencies. The bridge sets source paths to this checkout. No sponsor credentials or provider calls are needed.

## Feature and durability tests

`tests/test_meterless_world_model.py` checks real case integration, duplicate-evidence behavior, rebuilding the evidence projection, complete-envelope budgets and rejected history tampering. `tests/test_case_persistence.py` exercises independent database connections, global claim limits, atomic history/index updates, and killing a worker process before recovering its job. SQLite and PostgreSQL paths are exercised separately.

## Scope and limits

The passing upstream suite tests its eight specified invariants. It does not certify every optional capability of the broader architecture. Semantic embeddings, cross-case enrichment, automatic fuzzy entity merging, arbitrary operator merge/split workflows and vector memory are not advertised as implemented features. Current case evidence uses explicit external IDs, avoiding fuzzy identity decisions across trust boundaries. The graph is an evidence graph, not independent proof of causation.

Large canonical event streams still need retention/archive policy for sustained production workloads. No external certification, unlimited scale or arbitrary-code sandbox guarantee is claimed.
