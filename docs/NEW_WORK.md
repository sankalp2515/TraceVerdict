# TraceVerdict work record

## Subsequent verified implementation

The sponsor services are now configured. Added and verified a Python Meterless World Model Engine, its upstream conformance bridge, three independent PostgreSQL sources, native Zetaris USL/DQ, immutable replay captures and executor fingerprints, evidence-first critic checks, bounded formatting recovery, indexed durable history/jobs/object lookup, transactional global admission, browser sessions/CSRF, a real case-only Docker runtime, and backup/restore checks. A complete live synthetic case awaits human review. Current evidence and limitations appear in [RELEASE_VERIFICATION.md](RELEASE_VERIFICATION.md). The completed product frontend is now integrated at `apps/web`; see [frontend repository integration](FRONTEND_REPOSITORY.md). Pending-status statements in the initial record below are historical.

## Foundation

On 27 October 2026, a separate checkout was cloned from the user's IntentSeal repository at `E:\Claude Code Projects\AI Security` into `E:\Codex Projects\Open-Agent\traceverdict`.

Baseline commit: `afad26ac673a7adf94a78a0ea94e9c87f0bdc7b1`.

IntentSeal is the user's pre-existing product. The baseline includes its runtime, SDK, gateway, console, investigation, provenance, enforcement and evaluation functionality. Ownership does not make these features new hackathon work. Retain existing license and attribution files and declare pre-existing product components as required by the event rules.

The clone contains committed source and history. The original checkout's uncommitted `.gitignore` change, untracked presentation/artifact directories, local `.env` and virtual environments were not copied. The original checkout was not modified.

## New work in this checkout

- Added the `intentseal_gateway.cases` backend package: strict case/evidence/claim/repair contracts, CAS world state, source-linked graph, bounded Investigator/critic jobs, typed policy diffs, isolated replay, deterministic promotion and authenticated review/export.
- Added live Zetaris and Nightshift adapter code, using the existing OpenAI-compatible model adapter. Controlled HTTP tests exercise these contracts; live sponsor connectivity remains unverified.
- Added a Nightshift-only runtime profile to the existing configuration loader, overriding every legacy model role including the fallback Investigator role when explicitly enabled.
- Mounted the case routes in the existing gateway and added a separate synthetic-only sample API. No frontend files were changed.
- Added three deterministic synthetic examples, a sample runner, source export preparation, backend handoff docs and a backend-only sample Dockerfile.
- Added feature and API tests for evidence scoping, stale updates, model attribution, critic revision, job recovery, repair utility, receipt completeness, model-driven local replay and approval integrity.

## Current decisions and dependencies

- User selected a separate checkout and intends to target Track 2, The Agent That Can Explain Why.
- Track 2 eligibility for this extension has not been independently confirmed by an organizer.
- Sponsor credentials and working service endpoints are pending; installation progress is recorded separately in the parent workspace's SPONSOR_SETUP_STATUS.md.
- Install and verify sponsor services before claiming live integration. Record actual outcomes and add completed changes here as implementation proceeds.

## Validation

Baseline intent-contract and action-guard checks passed (45 tests) before changes. The first broader backend regression run passed 131 tests; additional replay/sample-API changes receive a final focused check recorded in TRACEVERDICT_VALIDATION.md. The three deterministic example cases reached AWAITING_REVIEW; each rejected the disruptive recipient restriction and passed the narrower contract candidate on six local checks.

These are local, bounded results. No real Zetaris query, Nightshift inference, Nemotron attribution, fresh dependency install, Docker build or frontend verification is claimed. Retain the final validation record and fixture limitations with any submission claims.


## Product frontend consolidation

Continued the supplied Lovable visual concept into a landing page and case workspace, then consolidated all frontend source, tests, assets, pinned dependency manifest, developer handoff and screenshot evidence into `apps/web` in this repository. Added root frontend commands and a dedicated CI job. The legacy IntentSeal console is retained. The product includes a five-step guided judge sample, actual recorded evidence/repair reports, source inspection, critic history, validation comparison, HttpOnly session integration, reviewer approval and export. The source no longer requires the standalone Lovable checkout. Frontend verification is recorded in `apps/web/docs/VERIFICATION.md`; consolidation checks are recorded in `docs/FRONTEND_REPOSITORY.md`. No new production deployment or fresh sponsor run is implied by moving the frontend.
