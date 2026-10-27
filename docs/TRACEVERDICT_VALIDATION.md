# TraceVerdict backend validation

**Historical validation log. See [current executed release verification](RELEASE_VERIFICATION.md) for the subsequent native USL, World Model, persistence, session and live acceptance results.**

## Later connectivity and readiness assessment

The original results below were recorded before sponsor credentials became available. A subsequent assessment on 27 October verified an authenticated Zetaris API-token query (`SELECT 1`, HTTP 200, column-array result), configured the backend's private sponsor settings, and retained the earlier real Nightshift Nemotron tool-call receipt. `SHOW TABLES FROM traceverdict` returned an empty result; a governed application join is still pending.

The six focused test files were rerun: **33 passed in 28.29 seconds**. One configuration test initially failed because the developer's private `.env` refilled a deliberately removed model setting. That test now mocks environment loading for isolation; no production configuration behavior changed. Separately, **2 secret-scanner tests passed in 0.21 seconds** after correcting classification of the public `METERLESS_MODEL` route; opaque credential matching and vendor-key pattern detection remain covered. Changed-file lint, the full repository secret scan and Git whitespace check passed. These checks are not a Git-history audit or proof of a complete live investigation. See `PRODUCTION_AND_SUBMISSION_READINESS.md` for the current assessment and release priorities.

## Original implementation validation

Date: 27 October 2026. Frontend work was excluded at the user's request. Sponsor credentials were unavailable.

## Executed checks

| Check | Result | Limits |
| --- | --- | --- |
| Baseline contract and action guard | 45 passed in 6.26 seconds | Before the new backend changes |
| Regression run covering new cases plus existing config, router, gateway, tenancy, contract and action guard | 131 passed in 107.79 seconds | Before the final model-replay, sample-server and historical-projection additions |
| Final focused case, repair gate, world state, integration-contract, API and model-replay checks | 33 passed in 31.41 seconds | Sponsor HTTP/model responses are controlled test doubles |
| Repository correctness lint | Passed | Static pyflakes/syntax checks using existing ruff configuration |
| Repository secret-pattern scan | Passed | Includes nonignored untracked files; not a credential-history attestation |
| Git whitespace check | Passed | Git emitted line-ending normalization notices for README and .env.example |
| Three synthetic example runs | All reached AWAITING_REVIEW | Deterministic templates, not model inference |

The interpreter came from the existing local IntentSeal development environment. PYTHONPATH and INTENTSEAL_HOME pointed to this separate checkout for tests. The example runner explicitly prepends this checkout's source packages. The original project's code and private environment file were not changed.

## Measured sample outcomes

`examples/traceverdict` contains the supplier-contact, invoice-forward and report-notify JSON reports. Each case records one critic revision and two repairs. The broad recipient restriction passes five of six checks but fails the explicitly authorized send and is rejected. Enabling the existing intent contract passes all six checks and reaches review. No patch is applied.

These cases reuse one fixture template. They do not constitute independent evidence of general security robustness, natural-language summarization quality, customer time savings, or sponsor connectivity. The model-driven replay tests exercise a scripted tool-calling model so that control effects, resistance and legitimate utility can be checked offline.

## Requirement status

| PRD item | Backend result |
| --- | --- |
| FR01 versioned intake | Implemented for frozen synthetic fixtures; old sessions explicitly retain historical-policy/replay gaps |
| FR02 Zetaris retrieval | SELECT-only scoped adapter and source export contract implemented; actual registration, joins and USL proof pending |
| FR03 investigation | Bounded tool-calling Nightshift path implemented and contract-tested; live inference pending |
| FR04 critic revision | Implemented with at most two revisions and inconclusive/incomplete outcomes; deterministic sample and controlled model tests pass |
| FR05 evidence graph | JSON graph, evidence drilldown and hash-checked historical projections implemented; rendering deferred |
| FR06 typed repairs | At most two supported candidates, trusted recipient checks, complete AgentPolicy validation and exact diffs |
| FR07 safety and utility replay | Fresh deterministic trials implemented; bounded model-driven replay implemented and tested with doubles; live trials pending |
| FR08 promotion | Frozen expectations and event-linked receipts determine outcomes; incomplete, disruptive and stale artifacts cannot pass |
| FR09 recommendation | Export includes evidence graph, hashes, diffs, manifests, results, reviewer and rollback hash; no production apply |
| FR10 sponsor model path | New live roles use Nightshift; optional Nightshift-only profile also overrides all legacy roles; concrete model proof pending |
| FR11 World Model | Application-owned reference-architecture subset implemented and feature-tested; no vendor conformance certification claimed |
| FR12 sample mode | Three examples and synthetic-only authenticated sample API run without sponsor keys |
| FR13 apply/rollback | Deferred P1; export is the MVP boundary |
| FR14 campaign view | Deferred P1 |

## Remaining release checks

1. Finish sponsor installations, obtain private credentials and verify real Nightshift model discovery/tool calling.
2. Register the actual three Zetaris source groups, create and retain proven connector/USL definitions, execute exploratory queries and a data-quality rule, and retain a live case join receipt.
3. Run the investigator, critic and repair roles through a real Nemotron-backed route; retain attribution rather than assuming it from a route name.
4. Execute live baseline/candidate agent trials, measure latency, and ensure the suite fits the bounded job deadline. Failure or timeout remains incomplete.
5. Expand and independently group the evaluation data to the PRD's larger target; current near-template examples are not that dataset.
6. Verify a fresh dependency install, Docker build, PostgreSQL operation and multi-process crash/lease recovery. Local SQLite feature tests alone do not establish these properties.
7. Implement and verify the frontend, then record the real workflow, build the deck and complete the submission package with the pre-existing-code declaration.

## Readiness conclusion

The backend has a locally verified synthetic vertical slice and tested live integration contracts. Production readiness and hackathon sponsor compliance remain **insufficiently evidenced** until the live checks above pass. No independent peer review, production deployment, sponsor inference or frontend verification is asserted.
