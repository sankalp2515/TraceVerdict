# NVIDIA Nemotron through Meterless Nightshift

The official FAQ awards the DGX Spark Founder's Edition for the best use of NVIDIA Nemotron through Nightshift. It does not publish a separate numerical award rubric. This product's case rests on implemented behavior and retained evaluation evidence, not an award prediction.

## Explicit role allocation

METERLESS_MODEL selects Nemotron 3.5 Lightning for investigator, critic and repair planning. METERLESS_REPLAY_MODEL explicitly selects Nemotron 3 Ultra for model-driven replay, through the same Nightshift transport. This is configured role allocation, not a silent fallback. New cases pin primary/replay routes, reasoning settings, adapter fingerprint and endpoint hash. Changes block validation/review of stale cases.

The product preserves actual response IDs, returned model IDs, usage, retries and durations. Unreturned provider fields remain null. Investigator claims cite scoped Zetaris evidence. Critic checks each claim. Planner output is restricted to typed policy paths. Models cannot approve or apply a policy.

## Repeated local comparison

[Full results](../examples/traceverdict/nemotron-evaluation.json), reproduced with `python scripts/nemotron_evaluate.py`.

| Route | Utility tasks | Unsafe trials | Successful-call p50 | Successful-call p95 |
| --- | --- | --- | --- | --- |
| Lightning | 15 passed, 3 failed | 6 resisted | 678 ms | 2715 ms |
| Ultra | 18 passed, 0 failed | 6 resisted | 2150 ms | 6163 ms |

Each route received the same 12 synthetic development tasks, repeated twice, over three document types. All 48 outcomes are retained. No provider errors occurred in this comparison. Both used actual NVIDIA model IDs returned through Nightshift. These results support using the slower Ultra route where correct legitimate action selection matters. They do not establish broad superiority, stochastic robustness or policy-control effectiveness. Unsafe resistance is model behavior; separate fixed-action tests establish enforcement.

## Complete live repair validation

[Invoice case with Ultra replay](../examples/traceverdict/live/invoice-forward-ultra/summary.json) uses real Zetaris evidence queries and Lightning reasoning. Its model-proposed patch passed 20/20 fixed-action tasks, and Ultra preserved eight of eight model-driven utility tasks. The disruptive API-origin comparison passed 18/20 fixed-action tasks and six of eight utility tasks, so the gate rejected it. The case awaits human review. No production policy changed.

Replay uses local outboxes and deterministic artifacts, not external sends or generated-summary quality. Earlier Lightning invoice/report utility failures and provider errors remain retained under examples/traceverdict/live. The comparison is a declared development evaluation whose prompts informed implementation, not an untouched benchmark. NVIDIA credentials stay inside Nightshift.
