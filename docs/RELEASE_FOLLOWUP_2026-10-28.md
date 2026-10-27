# Release verification — 28 October 2026 IST

## Product and access

The live product runs at http://localhost:5173. API, Node web, Caddy proxy and three PostgreSQL source services run independently in Docker with resource limits and persistent volumes. Zetaris runs in its installed Compose stack and Nightshift in its supported native runtime. The source data and cases survived a device reboot. Start/stop scripts preserve named volumes and perform a governed-query warm-up plus authenticated dependency checks.

The independent recorded demo runs at http://localhost:5174/workspace?mode=recorded&case=supplier-contact. `compose.demo.yml` requires no populated environment file, database, account, key or sponsor runtime. The default `docker compose up -d --build --wait` starts this demo; the historical runtime Compose file is retained as `compose.foundation.yml`. The demo uses the existing Docker bridge rather than allocating another subnet. The five-step route targets 3½ minutes from opening the application to report export. This is a suggested pace, not a measured usability result; installation and fresh provider execution are excluded. A byte-identical recording of the actual Nemotron run is accessible with `case=nemotron-live`. Viewing it runs no inference.

## Executed validation

- Full backend regression with PostgreSQL enabled: **329 passed, one skipped**, one existing LangGraph deprecation warning.
- Frontend TypeScript/product lint and **16 component/data tests passed**. Worker concurrency is bounded for stable runs on this resource-constrained workstation.
- Backend image and production Node web image built. The independent demo image built and its container is healthy.
- Demo landing, workspace, deterministic sample and recorded Nemotron JSON returned HTTP 200.
- Proxy sign-in, HttpOnly/SameSite cookie, authenticated listing, CSRF rejection, valid logout and post-logout 401 passed.
- Reviewer queue metrics returned scoped counts and no active jobs; the project credential received 403. Scope isolation and old-queue attention have test coverage.
- Offline original-capture schema validation passed without a credential or network call.
- Bounded local authenticated case-list smoke: 32/32 HTTP 200 requests at concurrency four; p50 492 ms, p95 1,172 ms over 5.2 seconds. This excludes model calls/writes and is not a production SLO.
- Ruff, Compose syntax and secret/publication scans passed. Existing World Model upstream conformance evidence remains 8/8.

## Live sponsor evidence

Fresh Docker case `case_242688de3dc4e21304b0ca31eaec` completed collection, governed evidence access, Nemotron reasoning and repair replay with zero errors. The targeted repair passed 20/20 fixed-action tasks and 8/8 live utility tasks. The restrictive API control was rejected at 18/20 and 6/8. Both model baselines resisted 12 unsafe prompts, which is not attributed to policy enforcement. No human approval or policy application occurred. [Case and receipts](../examples/traceverdict/live/docker-restart/summary.json).

The separate imported nonfixture capture also completed the live path and awaits review. Captures are operator-attested; the published original data is explicitly synthetic. The 48-trial development comparison retains every outcome and motivates Lightning for investigation/planning and Ultra for replay. See [NVIDIA evidence](NVIDIA_NEMOTRON_EVIDENCE.md).

The Docker endpoint fingerprint differs from the earlier host-process profile. Historical cases retain their original runtime fingerprint; they cannot be promoted across that change. The fresh case records the current profile.

## Presentation and submission

The final deliverable is `submission/TraceVerdict_Submission_Deck_v6.pptx`: 12 editable slides rebuilt around the supplied HTML reference's visual composition. It uses a split cover, navy scenario panel, solution panels, architecture flow, large evidence figures, business canvas and roadmap. Package/layout/font checks passed with zero findings; all slides were rendered and inspected. It is an adaptation, not an identical HTML import. Superseded exports are excluded from the current submission package.

Track 2 eligibility was confirmed by the team. Component lineage is recorded in [engineering provenance](NEW_WORK.md). The public repository is https://github.com/sankalp2515/TraceVerdict. The video and portal submission are still outstanding; see [the final checklist](SUBMISSION_FINAL_CHECKLIST.md).

## Remaining release gates

Browser automation is disabled in Work settings, so no fresh timed visual walkthrough or browser verification of newly added intake controls is claimed. The current application has component/API and actual sponsor execution evidence.

Original customer incidents require supported capture mapping, a private reviewer credential and configured sponsor services. Deployment removes local installation friction; it does not replace authorization or implement arbitrary tool adapters. Current replay executors are a local outbox and deterministic artifact reader. Approval exports a recommendation and never deploys production policy.

Before a broad multi-customer production release: choose and verify HTTPS hosting/network restrictions, identity and key provisioning, customer retention/legal-hold policy, external monitoring/alerts, measured capacity SLOs and whole-platform disaster recovery. Source restore checks do not establish full platform recovery. SSO and additional isolated tool executors are product milestones, not shipped capabilities.
