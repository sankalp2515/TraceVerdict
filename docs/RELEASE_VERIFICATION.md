# TraceVerdict release verification â€” 27 October 2026

The backend has a verified live synthetic workflow through real sponsor services. It is a production-oriented bounded MVP. The completed product frontend is now consolidated in `apps/web` in this repository; see [frontend integration and checks](FRONTEND_REPOSITORY.md). Production deployment and final submission remain separate release gates.

## Executed checks

| Check | Result |
| --- | --- |
| Full regression with PostgreSQL, before final replay/capture additions | 319 passed, 1 skipped; one LangGraph deprecation warning |
| Final focused Linux checks, fresh installed runtime with PostgreSQL | 52 passed, 1 skipped |
| World Model upstream conformance against this Python implementation | 8/8 passed |
| Native Zetaris data-quality rule | 63 total, 63 valid, zero invalid |
| Three independent sources | Three exploratory queries per source, plus semantic queries and completeness verification |
| Fresh Linux backend image | Built with constrained dependencies; non-root runtime |
| Container dependency connectivity | PostgreSQL, Nightshift and Zetaris online; readyz and authenticated connections returned 200 |
| Isolated PostgreSQL restore checks | Events 32, configuration 16, reference 8 evidence rows restored and matched at the time of check |
| Secret scan | Passed; private credentials remain excluded |

## Live acceptance

[Summary](../examples/traceverdict/live/summary.json), [report](../examples/traceverdict/live/report.json), [full trace](../examples/traceverdict/live/case.json), [Zetaris receipts](../examples/traceverdict/zetaris/native-usl.json).

Case `case_4965e7cff8b2901f74ab21b8fb77` is AWAITING_REVIEW. It uses a synthetic incident, real sponsor requests and local-only executors. No production policy was applied.

The model-origin repair passed 20/20 fixed-action tasks. Each model-driven baseline and candidate run produced eight utility passes and 12 unsafe resistances, with zero execution errors. Resistance means the model did not attempt an unsafe send; it is not a policy-control pass or a measured safety improvement. The separate fixed-action suite establishes enforcement, including purpose misuse of an approved contact.

The API-origin negative control was deliberately proposed by the acceptance script, not the model. It passed 18/20 fixed-action tasks and only six of eight model-driven utility tasks, so it was REJECTED. Blocking more actions cannot qualify by sacrificing legitimate utility.

Nightshift receipts returned `nvidia/nemotron-3.5-lightning-30b-a3b`. Missing vendor provider fields remain null. Zetaris evidence includes actual query receipt IDs and independent source versions. Full per-task outcomes are retained.

## Evaluation scope

Fixture v4 freezes 20 tasks: six development unsafe families, six distinct acceptance unsafe families and eight utility tasks. Acceptance payloads are withheld from the investigator and planner. The replay agent sees each task/document and chooses an action and recipient. The controller validates the choice, binds deterministic artifacts and checks policy before executing locally. This evaluates authorization, routing and side effects; it does not evaluate generated summary quality.

Earlier failed/incomplete runs remain in ignored local artifacts. Replay v3 exposed utility failures and was retired during development. v4 uses a typed action-selection function and a replay implementation fingerprint. Code changes invalidate further validation/approval for an old frozen case. This is a development acceptance suite, not an untouched external benchmark. Each model-driven task has one trial; broad stochastic robustness is unmeasured.

## Backend improvements now implemented

- Python World Model Engine powers the provenance-linked evidence graph and model context; the unchanged upstream conformance runner calls the actual Python engine through a bridge.
- Native Zetaris USL joins three independent PostgreSQL sources; native DQ and completeness queries validate the evidence contract. The application uses the activated USL through its stable view.
- Immutable generic captures bind original action/receipt identity, historical policy, source version, timestamp, model/tool references and replay inputs. Captures are operator attestations, not independent proof of authenticity.
- Project/reviewer scopes, tenant/agent isolation, HttpOnly browser sessions, CSRF/origin checks, request limits and scoped pagination support the frontend contract.
- Indexed durable history/jobs/object lookup, transactional admission, global worker limits, CAS and expiring leases support recovery. Tests kill a real worker process and terminate a dedicated database connection to check rollback/recovery.
- Bounded model calls, structured-output recovery, critic feedback, typed patches, hash-bound review/export, a clean Docker runtime and isolated backup/restore checks are implemented.

## Remaining release gates

1. Integrate the user's frontend at localhost:5173 with the API at localhost:8000. Verify login/refresh/CSRF, graph drill-down, polling, incomplete states, candidate comparison and reviewer export.
2. Have a human review the passing candidate. Approval exports a recommendation; it never deploys a policy. A connected production enforcement integration needs its own rollout/rollback verification.
3. Configure a reachable deployment with HTTPS, secure cookies, restricted platform/database networking and protected persistent storage. Loopback URLs are development endpoints.
4. Finish the actual 1â€“4 minute demo, deck with final product visuals, public repository, submission form and unauthenticated link checks.
5. Declare the pre-existing IntentSeal foundation accurately. Track 2 was selected by the user; organizer confirmation of extension eligibility has not been obtained.

The supplied deadline is 27 October 2026 23:45 UTC / 28 October 05:15 IST. Recheck the live portal before submitting.

## Production limits

Admission is bounded to 32 active jobs and two concurrent workers across instances sharing this database. These controls do not establish a throughput SLO. Each store uses one locked connection; current case aggregates and canonical World Model events still require retention/archiving for sustained workloads. Production needs measured capacity, migrations, operational metrics, identity/secret management and whole-platform restore drills.

The graph represents evidence relationships and supported explanations, not independent proof of causation. Hashes detect change but do not authenticate a compromised producer. Executors are a closed local outbox and deterministic artifact reader. Arbitrary code, real external sends, enterprise certification and unlimited scale are outside the verified scope.
