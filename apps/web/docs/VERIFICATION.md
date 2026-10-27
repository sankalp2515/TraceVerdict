# Frontend verification and reference comparison

Reviewed 27 October 2026. The supplied Lovable design is the active visual reference, not a newly generated replacement concept.

## Checks completed

- Production client/SSR/Cloudflare build: passed.
- TypeScript `tsc --noEmit`: passed.
- ESLint on new product features, routes, brand and data tests: passed.
- Vitest: nine tests passed, including outcome/receipt truth boundaries and recorded graph/candidate integrity.
- All three deterministic sample scenarios rerun against the current real backend: broad candidate 18/20 passed and rejected; targeted candidate 20/20 passed and awaiting review. The same underlying suite is reused; the three runs are not independent robustness measurements.
- Desktop browser: original reference at 1280 × 720; completed landing at 1440 × 1000; workspace at 1280 × 720 and 1440 × 1000. Mobile at 390 × 844. No page-level horizontal overflow in the landing or case overview; graph and result table scrolling remain local.
- Recorded workflow: all three cases open; supplier case survives refresh; graph node/source dialog, record-index search, keyboard edge selection, critic challenges, both candidates, failed-result filter, scenario receipt, disabled sample approval, mobile menu and FAQ expansion exercised.
- Real local backend with an isolated SQLite database and disposable QA-only credentials: project sign-in, new sample case, persisted investigation job, targeted and broad validation jobs, project-user approval restriction, reviewer sign-in, hash-bound approval, JSON export, session restoration and server logout exercised. Export contains one approval, status APPROVED and `applied: false`.

The in-app automation entry point timed out, so browser QA used Playwright Chromium CLI. The local preview was also sent to the Codex browser panel. Screenshots are retained under `output/playwright/`. Provider-backed live reasoning and real sponsor connection health were not exercised in this frontend verification. Their returned fields and explicit failure states are implemented, including separate model-driven replay trials and model/request evidence.

## Fidelity ledger

| Comparison point            | Original reference                               | Render evidence and decision                                                                                                                                                                               |
| --------------------------- | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Paper and navy palette      | `lovable-before.png`                             | `final-desktop.png`: retained exact theme variables and color temperature. Navy workflow band extends the original dossier surface.                                                                        |
| Typography hierarchy        | Original Spectral heading and IBM Plex body/mono | `final-desktop.png`, `final-mobile.png`, `graph-desktop.png`: retained families; shorter product copy and deliberate responsive wrapping.                                                                  |
| Hero illustration           | Original evidence-chain JPEG                     | `final-desktop.png`: same illustration, no tint overlay, framed as an evidence dossier. Explicit dimensions and high fetch priority.                                                                       |
| First-screen composition    | Original split headline/illustration             | `final-desktop.png`: retained split composition with simpler primary action and visible following principle strip at 1440 × 1000.                                                                          |
| Navigation and visible copy | Design-system navigation and actions             | Intentional change documented in DESIGN.md: product navigation and working workspace CTA replace showcase links. H1 is unchanged. No unintended visible-copy additions found in the final hero inspection. |
| Source/graph anatomy        | Lovable observed-versus-inferred graph concept   | `graph-desktop.png`, `evidence-source.png`, `edge-inspection.png`: actual source versions, full hashes, real relation bases and an equivalent searchable list.                                             |
| Policy comparison           | Original design primitives                       | `validation-desktop.png`: actual candidate operations, paired outcomes, derived counts, individual receipts and actual measured durations.                                                                 |
| Human gate                  | Signal/status semantics                          | `approved-recommendation.png`: actual server approval, exact artifact hashes, visible approval history and explicit no-production-change wording.                                                          |
| Responsive reading          | Reference required responsive retention          | `workspace-mobile.png`, `landing-mobile.png`, `final-mobile.png`: stacked panels and readable task/receipt distinction; no discarded source records.                                                       |

## Repairs made during QA

1. Replaced the original showcase's withheld-incident story with the actual application-reported sandbox execution.
2. Reran the current sample suite and replaced the older six-check recordings with fresh twenty-check reports.
3. Handled the omitted uncertainty field on newly created collecting cases rather than assuming a complete report shape.
4. Matched the backend's case-level review gate: all proposed candidates must finish validation; the selected candidate must independently pass.
5. Ignored cancelled session-restoration requests so development remounts cannot open a spurious sign-in dialog after a successful restore.
6. Displayed a saved approval as approved and disabled repeated approval UI, while retaining the server's underlying validation status.
7. Removed the dev-only imported-image query mismatch that caused a hydration warning.
8. Corrected QA screenshots to start at the top and wait for the deliberate hero entrance. Immediate reload screenshots had captured restored scroll positions and intermediate animation frames.

The graph paths are narrow visual targets; keyboard selection and the record-index relationship list are verified alternatives. A browser locator clicking the center of an SVG group's bounding rectangle can miss the curved stroke; this was not treated as proof of a broken click handler. Node and source interaction were exercised through actual browser clicks.

## Remaining release work outside this frontend change

No public deployment or domain was configured. Live sponsor/provider availability and production HTTPS/cookie/CORS configuration must be checked on the actual hosting environment. Commercial prices, customer endorsements, enterprise SSO and production policy application were not fabricated. The local checkout is a frontend implementation with verified sample/API workflows, not a certification of all production services.

## Judge-experience follow-up

Removed design-system links from public and workspace navigation. The former URL now redirects to the supplier sample. The landing's Start the guided demo action opens that case directly without sign-in. Added a five-question guided sequence with next/previous actions, derived repair results, in-context source instructions and report download. Agent/connection setup navigation is hidden in recorded mode; exiting the guide restores normal workspace navigation.

Playwright verified the landing-to-sample path, all five guided steps, failed-utility and passing-check counts, recorded report download, exiting/reopening guidance, the old-URL redirect, and the 390 px responsive layout without page overflow. No page runtime errors were observed in that walkthrough. This does not substitute for first-time human usability testing.


## Consolidation

The application now lives in the backend repository at `apps/web`. A fresh lockfile install, root frontend check (nine tests), production build and browser walkthrough were repeated from that location. See `docs/FRONTEND_REPOSITORY.md` at the repository root. The active local server now uses the consolidated checkout, not the original Lovable folder.
