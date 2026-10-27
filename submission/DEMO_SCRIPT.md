# TraceVerdict demo script

Target length: 3 minutes 20 seconds. Record the real application or a walkthrough of the retained real backend run. Show the exact case ID and mode. Label prerecorded execution as a recorded run. Keep credentials and populated environment files off screen.

| Time | Show | Narration |
| --- | --- | --- |
| 0:00–0:20 | Case overview and authorized task | TraceVerdict helps teams investigate an agent action and test a repair. This synthetic supplier incident uses real Zetaris and Nightshift requests. The user asked for a summary and prohibited contacting anyone. |
| 0:20–0:45 | Document, attempted send and matching receipt | The document contains an instruction to contact an auditor. The action and application receipt show what the local executor reports actually happened. The historical sandbox policy had intent enforcement off. |
| 0:45–1:10 | Evidence graph and one evidence detail | The World Model Engine connects the task, document, policy and receipt to the explanation. Each claim links to source evidence and its version. Context edges and inferred influence do not establish independent causal proof. |
| 1:10–1:35 | Actual explanation and critic rounds | The investigator proposes cited claims. The critic checks each claim against the supplied evidence. Show the actual disputed claim and subsequent revision from this case, if present. Keep uncertainty visible. |
| 1:35–2:10 | Candidate policy diff and replay comparison | The model proposes a bounded repair. Fixed-action replay directly tests enforcement. Model-driven replay separately checks whether the agent completes authorized tasks. Show the full task counts and distinguish unsafe resistance from a control pass. |
| 2:10–2:35 | Rejected comparison control | This deliberately disruptive API-origin comparison loses legitimate messaging utility. The gate rejects it even if it blocks unsafe actions. It was a comparison proposed by the test harness, not a second model recommendation. |
| 2:35–3:00 | Sponsor evidence and returned model IDs | Zetaris joins three independent sources through native USL and runs a native quality rule. The Meterless World Model powers graph state and passes its upstream conformance suite. Actual model receipts show the NVIDIA routes passing through Nightshift. |
| 3:00–3:20 | Review and recommendation export | A human reviews the exact base policy, patch and validation hashes. Approval exports the recommendation and rollback reference. It does not deploy a production policy. TraceVerdict extends our pre-existing IntentSeal enforcement foundation with this investigation and validation workflow. |

Before recording, use the latest validated case in examples/traceverdict/live/summary.json. Use its actual metrics and returned model IDs. The frontend must display those values from the backend. Do not animate invented fresh reasoning or use a template report as a live inference result.

The integrated product frontend is in `apps/web` in the same submission repository. Start it with the root `npm run frontend:dev` command after `npm run frontend:install`. The guided no-account sample is explicitly recorded and synthetic. For a live sponsor demonstration, connect the workspace to the case API and select the actual validated live case. Do not narrate the recorded sample as a new sponsor inference run. Frontend screenshots are retained under `apps/web/output/playwright`; use the actual case and mode in the final deck.
