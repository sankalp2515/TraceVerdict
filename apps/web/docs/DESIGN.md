# TraceVerdict design and experience

## Product understanding

TraceVerdict is a case investigation and policy recommendation workspace built on IntentSeal. Its primary users are engineers and analysts investigating suspicious AI-agent tool actions. An authorized reviewer evaluates a specific policy change after safety and legitimate-task replay. Approval exports a recommendation; it does not apply a production policy.

Source material reviewed: the local product PRD, implementation guide, `traceverdict/docs/FRONTEND_AGENCY_PRODUCT_BRIEF.md`, `FRONTEND_INTEGRATION.md`, backend architecture, API implementation, schema, fixture reports and recorded world-state aggregates. The existing Lovable app was run and inspected before replacing its entry page. The visible Google Docs tab was not needed to infer product requirements: the corresponding extracted PRD and guide were available locally.

## Existing concept and deliberate continuation

The accepted reference is the supplied Lovable project. Its concept is “forensic dossier, precision instrument”: warm paper, navy ink, Spectral headings, IBM Plex controls, subdued borders, an evidence-chain illustration, and semantic outcome colors. The original reference capture is `output/playwright/lovable-before.png`. Design references remain in the local development handoff. The old `/design-system` bookmark redirects to the guided sample; no design-system page is exposed to product users.

The reference was a public explanation of design decisions rather than a working product. The continuation turns `/` into a visitor journey and adds `/workspace` for the actual user task. No replacement stock imagery or unrelated visual concept was introduced. One correction was necessary: the original story showed a withheld action, while the actual fixture receipt reports execution in a deliberately permissive local sandbox. The product now uses the actual record.

## Tokens and rationale

| Token         | Reference hex | Meaning and reason                                                                          |
| ------------- | ------------- | ------------------------------------------------------------------------------------------- |
| Ink           | #142139       | Navy for evidence and readable structure; quieter than pure black against paper.            |
| Paper         | #faf7f1       | Inherited dossier ground; sustained investigation reading and visual continuity.            |
| Signal        | #dd5406       | Enforcement/review boundaries and the inherited top gate line; not a generic success color. |
| Verified      | #286d45       | Tests and recorded pass states; never used to imply universal safety.                       |
| Reported      | #305686       | Application-reported facts, inspected records and selected interaction states.              |
| Uncertain     | #a26f17       | Unknown, incomplete, inferred, stale and pending review states.                             |
| Contradiction | #b7191c       | Conflicts and explicit failure; not every incomplete result is an error.                    |

The implemented color source of truth remains Lovable's OKLCH tokens in `src/styles.css`. Hex values above are reference labels rather than a second independently maintained palette.

Spectral carries the written finding and product identity. IBM Plex Sans carries navigation, explanations and controls. IBM Plex Mono is limited to exact identifiers, policy paths, hashes and source content. Headings use a restrained 32–76 px responsive scale; primary body content is 14–18 px. Dense record metadata uses 10–12 px with accessible zoom and wrapping. Long prose stays below roughly 80 characters per line.

Marketing uses a 1,200 px maximum container, 48 px desktop gutters, and 20 px mobile gutters. Major sections use 55–108 px vertical space. The workspace has a fixed 235 px desktop navigation rail, a flexible main column, 35 px content gutters, and a top navigation layout on small screens. Two-column reading and comparison panels collapse to one column; tables and graphs retain deliberate local scrolling rather than causing page overflow.

Radii use 3–7 px: documents and controls should feel filed and precise. Hairline borders divide evidence; shadow is reserved for the editorial illustration and actual modal elevation. The sample dossier uses offset paper edges as its one physical motif. Lucide outline icons share 1.5–2 px strokes, with descriptive text carrying meaning. The fingerprint mark connects the product to traceability without claiming cryptographic identity verification.

## Visitor journey and conversion rationale

| Section                          | Decision supported                                                                                                                                     |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Hero                             | Makes the job understandable in one screen and offers a no-account sample. Existing illustration preserves brand recognition.                          |
| Evidence principles              | Establishes the product's specific trust contract without invented adoption metrics.                                                                   |
| Product problem and capabilities | Explains why prompts, logs, policies and receipts need one case. Each capability maps to a user question.                                              |
| Five-stage workflow              | Makes the sequence and human decision boundary visible before asking visitors to connect a deployment.                                                 |
| Inspectable case study           | Uses the supplied synthetic supplier incident as the proof. Identifies the rejected broad repair and passing bounded alternative honestly.             |
| Assurance                        | Addresses source integrity, outcome wording, exact review artifacts and failure handling.                                                              |
| Access and pricing presentation  | Offers recorded samples or an existing deployment. No published commercial price exists, so no prices, subscriptions or sales promises are fabricated. |
| FAQs                             | Handles causal uncertainty, provider failures, credentials and approval versus production application.                                                 |
| Final action                     | Repeats the same low-friction sample action after visitors have the context to evaluate it.                                                            |

Social proof is supplied by inspectable product evidence, not invented customer logos, endorsements or case-study performance metrics. Integration names describe architecture, not customer relationships or current connection health.

## Workspace map and interactions

- Cases: search only loaded cases, filter workflow status, cursor pagination from the backend, open recorded examples, or create a server-backed case.
- Overview: authorized task, attempted action, application-reported outcome, evidence availability, exact policy hash and next permitted action.
- Evidence: keyboard-selectable nodes and edges; a searchable record index offers the same source path; each relationship exposes its basis and supporting IDs. Modal drilldown displays escaped payload, source locator/version, hash and query receipt. History links download exact server projections.
- Explanation: claims, cited sources, inference/observation basis, alternatives, missing evidence and actual critic rounds.
- Repairs and validation: selectable candidates, exact before/after operations, origin, paired baseline/candidate outcomes, measured duration, receipt inspection, category/result filters and limitations.
- Review: specific candidate, base/patch/report/manifest hashes, explicit review checkbox, reviewer-only server approval, rejection/stale states, review history and report export.
- Agents and connections: authorized agent inventory and backend-reported dependency status. Recorded samples never claim live connection health.

Dialogs use native modal focus containment, Escape dismissal and named controls. Tab arrows move keyboard focus and selection. Graph meaning is conveyed by labels and line styles as well as colors. Skip links, visible focus, semantic landmarks, responsive layouts and reduced-motion behavior are implemented.

Motion is subordinate to reading: a single initial hero entrance, brief interaction state transitions, native expand/collapse, and a spinner only while work is actually pending. Graph layout does not jump or simulate autonomous thinking. No invented progress percentages are shown.

## Reference inventory and intentional copy changes

Retained: product name; “A conclusion you can inspect.”; editorial evidence image; paper/ink palette; serif/sans/mono roles; semantic state colors; evidence → explanation → validation → review narrative.

Replaced navigation: Story/Flow/Graph/Foundations/Components/Motion becomes The product/How it works/Built on evidence/Access, with Open workspace as primary product navigation. Development navigation is removed from the product.

Hero actions now say “Explore a sample case” and “See how it works”; their destinations are a usable workspace and the workflow section. The long concept paragraph becomes three short outcome-focused sentences. The “Design system · v1” badge is removed from the customer landing page. These are intentional product-facing changes, not visual drift.

## First-time evaluation flow

The landing action opens the supplier sample directly without credentials or case selection. A five-step in-product guide answers what happened, what supports the finding, what remains uncertain, which repair preserves utility, and what a reviewer approves. Each step has a clear next action and inspectable evidence below it. Repair counts are derived from the report. Recorded sample navigation omits agent setup and connection status. Explore freely dismisses guidance and restores the standard workspace tabs. The former design-system URL redirects to the sample. No external document is required for this path. First-time comprehension still needs validation with real people; browser checks establish working navigation, not universal usability.
