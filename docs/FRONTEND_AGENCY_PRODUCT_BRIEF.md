# TraceVerdict — product and frontend agency brief

Backend update, 27 October: case listing, agents, connection status and revocable browser-session endpoints are now implemented. Read `FRONTEND_INTEGRATION.md` for the current authentication, CORS and pagination contract; it supersedes the earlier pending-contract notes below.

## Product in one sentence

TraceVerdict helps teams investigate suspicious AI-agent actions, connect conclusions to evidence, and compare tested policy repairs before a human approves a recommendation.

The attached architecture calls the feature “IntentSeal Explain.” TraceVerdict is the current product working name; IntentSeal is its underlying runtime protection foundation. Naming clearance has not been performed.

## The problem and intended users

An AI agent can read an untrusted document, misinterpret an instruction inside it, and attempt an unauthorized tool action. Teams then have to reconstruct the user's task, document, attempted action, applicable policy and application receipt from separate systems. A quick policy restriction may stop the attack while also preventing legitimate work.

Primary user: an AI application engineer or security analyst responsible for connected agents. Reviewer: an authorized engineering/security lead deciding whether a tested policy recommendation is acceptable. A product owner may consume the exported incident summary and validation evidence.

The user wants to answer:

1. What did the user authorize?
2. What did the agent attempt, and what does the application report actually executing?
3. Which evidence supports the explanation, and what remains uncertain?
4. Which policy change addresses the problem while preserving legitimate tasks?
5. Which exact artifact was reviewed and approved?

## A concrete demonstration story

A research agent is asked to summarize a supplier report without contacting anyone. The report contains an instruction to send information to an unauthorized recipient. TraceVerdict presents the original task, untrusted instruction, attempted send, policy snapshot and local sandbox receipt in one case.

The investigator proposes an explanation. A critic challenges causal overclaims or missing facts. The system proposes bounded policy changes and evaluates them against unsafe and legitimate tasks. A broad recipient restriction can be rejected because an authorized send fails. A more targeted intent-contract change can proceed to review only if its actual safety and utility tests pass.

This is a synthetic sandbox scenario. Results must come from the supplied backend report; the interface must not invent a passing alternative, a critic exchange or fresh model execution. An approval produces a recommendation/export. It does not silently deploy a production patch.

## The product experience

Build an investigation workspace organized around a case. The main artifact is a traceable report with supporting evidence and repair comparisons. Conversation can be supplementary, but the primary workflow is case → evidence → explanation → validation → review.

The agency can choose the visual language. Prioritize legibility, clear evidence relationships, precise status wording, accessible interactions and a focused desktop investigation experience. A responsive layout must retain the same information on smaller screens through panels or tabs. Avoid designing around fabricated global safety scores or decorative model activity.

## Information architecture and screens

| Screen or area | User purpose | Essential content and actions |
| --- | --- | --- |
| Cases / entry | Find or create an investigation | Agent/session or supported synthetic fixture, mode, status, created time; create/open case using the paginated list endpoint |
| Case overview | Understand the incident quickly | Authorized task, execution outcome, agent/case IDs, live/sample label, snapshot availability, workflow status, missing evidence and next permitted action |
| Timeline and evidence | Inspect operational facts | Task, document, action, policy/tool snapshot, trusted reference and application receipt; source locator/version, content hash and query receipt where available |
| Evidence graph | Follow support and uncertainty | Evidence and claim nodes, labeled edges, observed versus inferred/context styling, selection and a detail drawer; synchronized list/table alternative |
| Explanation and critique | Understand the conclusion and its limits | Cited claims, competing explanations, disputed/accepted status, critique rounds, unresolved evidence and uncertainty |
| Candidate repairs | Compare bounded recommendations | Up to two candidates, rationale claim links, exact before/after policy diff, expected control effect, base/patch hashes and validation action |
| Replay comparison | Evaluate safety and retained utility | Baseline versus candidate; per-scenario category, execution mode, expected/observed outcome, application receipt, errors and measured duration |
| Human review and export | Review a specific immutable result | Exact case, candidate, base hash and report hash; reviewer-only approval; recommendation bundle download and limitations |
| Connections/status, if included | Explain integration availability | Real, cached or unavailable status for data/model paths through `GET /v1/connections` |

Do not require every screen to be a separate page. A case workspace with a stable header and focused tabs/panels is suitable. The agency should supply navigation and responsive interaction proposals.

## The graph is a primary interaction

Nodes currently represent task, document, action, receipt, policy, tools, reference/event evidence and claims. Available edges include `supports`, `application_reports` and `case_context`.

Clicking a node should reveal its actual evidence or claim. Clicking an edge should reveal the relation, basis and supporting record IDs. Explain solid observed support and dashed inferred/context relations with text and a legend; color alone is insufficient. Offer keyboard navigation and a searchable evidence list so the graph is not the only access path.

Never display an inferred edge as established causation. A policy record being present in a case does not prove it was the policy enforced for a historical action. Source versions and missing snapshots must remain visible.

## Wording and states

The four execution outcomes have different meanings:

| Label | Meaning |
| --- | --- |
| Withheld | Enforcement withheld the action, or an application receipt reports no execution |
| Allowed but unconfirmed | An action was allowed but there is no confirming application receipt |
| Application-reported executed | The application says it executed; this is not independent attestation |
| Contradiction | Application-reported execution conflicts with a recorded block/escalation |

Case workflow states are `COLLECTING`, `EXPLAINING`, `CRITIQUING`, `PROPOSING`, `VALIDATING`, `AWAITING_REVIEW`, `APPROVED`, `REJECTED`, `INCONCLUSIVE`, `INCOMPLETE` and `STALE`. Job states are `queued`, `running`, `complete` and `incomplete`.

`AWAITING_REVIEW` means the candidate passed the configured test gate; it is not a guarantee of universal safety. `APPROVED` means the identified recommendation was approved; it does not mean deployed. `INCOMPLETE`, `INCONCLUSIVE` and `STALE` must not use the same success treatment as a passing result.

Show provider failures and missing receipts explicitly. A resisted attack means the model did not attempt the unsafe action; it is not proof that the changed control blocked it. Show error, unknown, pass, fail and resisted separately. Display percentages only when derived from explicit counts and a stated denominator.

## Live, sample and recorded modes

- **Live:** evidence is retrieved through Zetaris and reasoning is requested through Nightshift. Show returned model and request evidence where available.
- **Sample:** deterministic synthetic workflow that works without sponsor services. Label it persistently; no model inference occurs.
- **Recorded:** a saved result of a previous run, if this mode is added to the UI. Show its run time and original execution mode. Do not label a recording as a new live run.

Live failures must not silently change a case into sample mode. The case's execution mode and intake snapshots are immutable.

## Backend integration contract

The backend is Python/FastAPI with JSON REST APIs. The checked-in schema is `docs/traceverdict-openapi.json`. Existing console assets come from the IntentSeal foundation; the new TraceVerdict screens are not implemented yet.

| Operation | API |
| --- | --- |
| Create case | `POST /v1/cases` |
| Read case | `GET /v1/cases/{case_id}` |
| Read graph | `GET /v1/cases/{case_id}/graph` |
| Evidence drilldown | `GET /v1/cases/{case_id}/evidence/{evidence_id}` |
| Historical projection | `GET /v1/cases/{case_id}/history/{version}` |
| Begin investigation | `POST /v1/cases/{case_id}/investigate` |
| Poll job | `GET /v1/cases/{case_id}/jobs/{job_id}` |
| Submit supported candidate | `POST /v1/cases/{case_id}/repairs` |
| Begin validation | `POST /v1/repairs/{repair_id}/validate` |
| Read validation | `GET /v1/validations/{validation_id}` |
| Approve recommendation | `POST /v1/repairs/{repair_id}/approve` |
| Export recommendation/report | `GET /v1/cases/{case_id}/export` |

Creation/investigation/validation requests use idempotency keys. Long operations return a job; the UI should poll its status, survive refresh and show the persisted result. Use bounded polling and stop on terminal status. Handle 409 stale/conflicting operations, 422 unsupported input, 429 rate limits and unavailable dependencies as explicit states. Do not infer progress percentages from a job status.

Approval must send the displayed `base_policy_sha256`, `patch_sha256` and `validation_report_sha256`; stale artifacts require refresh and re-review. Approve only the selected candidate that actually passed, even when another candidate in the same case failed.

Case listing, pagination, agents, connection status and browser sessions are now implemented; use `FRONTEND_INTEGRATION.md`. Full-text case search and enterprise SSO remain future scope. There is no production apply/rollback API in this MVP.

## Identity, privacy and review

The backend distinguishes project and admin scopes. Read and workflow actions require authorized project access; approval and source export require admin access. The new server-mediated session flow supports HttpOnly cookies, CSRF checks, expiration and revocation. Administrator credentials must never be embedded in browser code or shipped by an agency.

The browser must communicate with the application backend, not directly with Zetaris or Nightshift using sponsor tokens. Render attacker-controlled documents, claims and tool arguments as escaped text. Do not execute source HTML, scripts, Markdown HTML or arbitrary graph labels. Hide no missing-evidence warnings. Do not ship real API keys, user data or sponsor administration screens as design fixtures.

## Design deliverables and acceptance

Request a screen map, key user flows, design system, responsive components, loading/empty/error states, interactive graph behavior and an accessible implementation handoff. Deliver a connected prototype using the real sample API before polishing secondary dashboards.

Acceptance walkthrough:

1. Create/open a labeled sample case and return to it after refresh.
2. Distinguish attempted action from application-reported execution.
3. Open a graph node and inspect its source evidence; open the same record from the list.
4. Read a claim and its critique, including uncertainty.
5. Compare exact policy diffs and real safety/utility outcomes for two candidates when present.
6. See a failed/incomplete candidate remain unapprovable.
7. Review and approve only an eligible exact artifact under authorized credentials.
8. Export the report and retain its limitations and execution mode.
9. See honest provider-outage, missing-snapshot and stale-review states.

## Current maturity and future scope

Implemented: backend synthetic workflow, evidence/graph contracts, bounded model-role adapters, typed repairs, fixture replay, deterministic gates, approval/export and sample examples. Verified connectivity: real Zetaris API token/query and Nightshift Nemotron tool calling.

Still being completed: governed Zetaris case views, full live case execution, World Model conformance evidence, broader evaluation and reproducible production deployment. These are backend responsibilities, not graphic design work.

Future scope after the core workflow is proven: complete real-incident replay capture, controlled apply/rollback, richer identity/roles, cross-case campaigns and stronger operational scale. Keep these separate from screens promised for the hackathon MVP.

Product value to communicate: **a conclusion you can inspect, and a repair recommendation tested against both unsafe behavior and legitimate work.** No measured customer time-saving or broad security-effectiveness claim is established yet.
