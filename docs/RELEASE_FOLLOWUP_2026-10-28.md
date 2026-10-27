# Release follow-up - 28 October 2026 IST

The frontend is consolidated in apps/web. TypeScript, product lint, nine original tests and the production SSR build passed before the latest intake additions. Reviewer-controlled registration/capture/source publishing now provides a nonfixture integration path. Backend onboarding/scoping/integration/package checks passed (17 tests); a final full regression and new frontend intake checks follow separately.

## New live proof

Case case_c4e5c995cf8b32890863d06206c1 registered a new agent, imported original captured data with no fixture ID, published seven records, queried them through Zetaris and passed 20/20 validation tasks. It awaits human review. The originals were explicitly synthetic, newly instrumented local execution. This proves the customer-capture workflow, not a customer production deployment. [Case/report](../examples/traceverdict/live/imported-capture/report.json).

The invoice case with explicit Ultra replay passed the complete positive/negative gate. [Results](../examples/traceverdict/live/invoice-forward-ultra/summary.json). The [repeated Nemotron comparison](NVIDIA_NEMOTRON_EVIDENCE.md) retains 48 trials and Lightning's utility failures. Earlier incomplete runs remain retained. No model score, cost saving or generalized reliability is inferred beyond these runs.

Runtime route/settings changes now block validation/approval of old cases. Current reports pin adapter, endpoint hash, primary route and replay route. Historical reports remain valid evidence of their original execution but are not automatically promotable under changed configuration.

## Product readiness

Implemented: evidence graph and drill-down, investigator/critic revisions, deterministic claim checks and feedback, typed repairs, frozen manifests/executor fingerprints, fixed-action/model replay, hash-bound review/export, durable indexed jobs, worker recovery, scoped browser sessions, customer agent registration and capture import, managed source publication and clean backend/frontend builds.

Still required beyond the video:

1. Select/publish the final public repository and verify anonymous access. No new GitHub destination has been supplied; do not push to the original IntentSeal remote by assumption.
2. Finalize the deck with current product screenshots and current Nemotron role evidence, then verify public deck/repository links.
3. Complete the portal's team/profile/track/submission details and disclose the prior IntentSeal foundation. The official FAQ associates extending existing projects with Wildcard. Track 2 eligibility for this extension needs resolution; code ownership does not remove disclosure.
4. If judges should use a hosted service, select a server/domain and verify full-stack HTTPS, secure cookies, provider reachability and restricted database/platform access. Hosting is not listed as mandatory. No platform is prescribed.
5. Provision scoped judge access and test an original supported capture. Broad arbitrary-tool/connector self-service is not supported. Supported local tools and configuration boundaries are documented in CUSTOM_INTEGRATIONS.md.
6. Finish the actual production release checks: full-stack restoration, retention/deletion, measured capacity/SLOs, runtime dependency review, operational alerts and controlled downstream rollout. A local passing MVP is not enterprise certification.

The local browser is disabled in Work settings. New intake controls therefore have static, component/API and integration verification, not a fresh browser walkthrough. Earlier UI screenshots describe the earlier workflow. Do not claim browser verification of controls added afterward.

The external review correctly prioritizes a real complete workflow and safe utility-preserving repair comparison. Its statement that governed Zetaris/live execution is incomplete is stale. Proposed scores are speculative. A cinematic exploration cannot replace the actual working workflow. NVIDIA award strength should come from real Nemotron decisions, role allocation, repeatable evaluation and visible returned receipts.

The current official FAQ confirms Cursor optional, permits any cloud, and specifies video/deck/public repository/sponsor explanation. See DEPLOYMENT_REQUIREMENTS.md. Use the earlier organizer-stated submission deadline, 28 October 05:15 IST.

## Final checks completed

Full backend regression with PostgreSQL enabled: 328 passed, one skipped, one pre-existing LangGraph deprecation warning. The skip is the PostgreSQL-only fault check on the SQLite parameter. Package-data synchronization fixed the NOTICE mismatch detected by the preceding run.

Production Node frontend image built successfully and served /, /workspace and recorded sample JSON with HTTP 200. Production compose syntax validated. Vite and Zod advisories were resolved with patched versions (Vite 8.3.5, Zod 4.6.7); npm audit returned zero known vulnerabilities. This does not certify that every runtime dependency is vulnerability-free. No public deployment or TLS endpoint has been verified.

Final frontend TypeScript/product lint and all 12 tests passed after the patched Vite/Zod upgrades, including three new intake component checks. The final narrow backend onboarding/package check passed seven tests after the registration race handling adjustment. Ruff and the publication secret scan passed.

The production web build after patched dependency updates passed. Added CI to rerun the unchanged World Model conformance suite against the actual Python engine; cloud CI execution awaits repository publication. The full source secret scan, Ruff and package-data synchronization check passed. The updated 13-slide deck includes measured Nemotron allocation and retained limitations.

Added actual prior frontend graph imagery to the updated submission deck, explicitly labeled as a recorded synthetic case. New onboarding controls are not represented as browser-verified by that older capture. Final deck is submission/TraceVerdict_Submission_Deck_v4.pptx once its export/validation completes.

Final 14-slide deck exported and passed package/layout/font checks with zero findings. It includes an actual earlier frontend screenshot, clearly labeled synthetic, and the measured Nemotron comparison. The final filename is TraceVerdict_Submission_Deck_v4.pptx.

## Published verification

Public repository: https://github.com/sankalp2515/TraceVerdict (main). Implementation commit e2acb50 passed GitHub backend CI (328 passed, one skipped), frontend checks and the unchanged upstream World Model conformance suite. Anonymous repository, README and NVIDIA-evidence links returned HTTP 200. No private environment files, node_modules or build outputs were committed. Historical scanning checked 1,002 text blobs without credential-pattern/private-value matches.

Both backend and Node web images built. The clean backend image reproduced all three deterministic examples with networking disabled. Local Caddy routing served the frontend and /api, and cookie sign-in/list/logout passed through the proxy. This was explicitly an HTTP loopback check, not verification of a public domain or TLS certificate. Temporary proxy/web check containers were stopped after verification; the main local backend remains on port 8000.
