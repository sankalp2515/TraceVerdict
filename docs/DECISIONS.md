# Design decisions

Why IntentSeal works the way it does. Code comments refer to these numbers (`D-0xx`). Component IDs (`CORE-`,
`SDK-`, `PRX-`, `API-`, `CON-`, `EVAL-`) are described in [ARCHITECTURE.md](ARCHITECTURE.md).

## Principles

| # | Decision | Why |
|---|---|---|
| D-011 | Classifiers are **escalation signals, never deciders**. Final decisions come from deterministic rules and the policy, informed by the AI judge and the action guard | Off-the-shelf prompt-injection classifiers measured 52% false alarms on hard benign text, or 40% recall; neither can decide alone |
| D-015 | **Structural rules** at Tier 0: non-visible content, invisible and look-alike characters, encoded blobs, mixed scripts, forged role markers. Phrase signatures only from licensed open-source rule sets, loaded as data | Robust to rewording; no hand-written attack phrasing in the product |
| D-016 | **Library-first** Unicode repair, look-alike handling and decoding; engineering effort goes to containment (action guard, pinned fields, outbound scan, session risk, policy) | Proven libraries for the hard Unicode cases; containment limits damage when detection misses |
| D-027 | Human approvals resolve an ESCALATE only, once, for the same session, tool and arguments; never a BLOCK | Reviewers can unblock legitimate work without being able to click away a secret leak |
| D-005 / D-010 / D-014 | **Attack test cases come from open-source generators** (promptfoo, garak) and public research data; the project does not hand-write attack payloads. Generators own generation and delivery; the project serves targets, benign sets and deterministic scoring | Reproducible, credible, licence-clean evaluation; avoids training the evaluation on our own phrasing |

## Detection

| # | Decision | Why |
|---|---|---|
| D-013 / D-019 | Tier 0 rules on all content; **Tier 1 scores all untrusted content and user turns**; chunks at or above the escalation band go to the judge; scans cached by content hash | Plain-text attacks without a structural signal must still reach the judge |
| D-020 | Short document metadata (≤ 12 words: titles, authors) counts as visible | Every titled PDF was being neutralised |
| D-023 | **Decode before scoring**: base64/base64url, hex, Unicode tag characters, %-encoding and rot13 become extra detection views; look-alike text reaches the judge folded by shape | Encoded instructions were otherwise invisible to the classifier and judge |
| D-024 | Policy `judge_untrusted: always` for agents with high-risk tools: every untrusted document (≥ 40 characters) is assessed by the judge; user turns keep the classifier gate | The classifier scores paraphrased third-party instructions near zero |
| D-026 | Trainability: confirmed attacks are stored as keyed fingerprints (hashed word shingles, never text) and matched at Tier 0; false-alarm marks are exact and per agent and never waive structural rules or the action guard | Reviewer feedback improves the next decision without storing content |
| D-030 | Judge prompt changes are evaluated on the development set only; the held-out set is never used for tuning | Keeps the held-out false-alarm rate honest |
| D-041 | **Long documents**: windows of the most suspicious chunks (8 × 6,000 characters by default), evidence mapped to original offsets; anything that cannot be assessed is held (`oversize-hold`); input limit 1,000,000 characters | The judge must not silently read only the beginning of a document |
| D-047 | Explicit-intent rule for high-risk tools (`intent_terms`), decoded views in the outbound scan, forged chat-template markers stripped from content (not from source code) | Unrequested actions (confused deputy) and template-token forgery were the attack families that beat other guardrails in public agent-security competitions |
| D-051 | **Real web pages**: short non-visible web text (≤ 12 words: alt text, tooltips, ARIA labels, technical meta, build comments, menus) is ordinary text; hidden text in HTML, HTML email and Markdown always goes to the judge and is quarantined unless the judge clears the document; hidden text in PDF and Word is quarantined regardless; a structural flag never shields the rest of a document from Tier 1 and the judge; judge windows packed most-suspicious-first | Measured on 13 real sites: every page was being flagged and a second page in a session was held |
| D-054 | Text written largely in look-alike letters (≥ 3 mixed-script look-alike words and ≥ 25% of words) is quarantined whatever the judge says (`drop-lookalike-text`) | Obfuscation, not language: real multilingual text keeps each word in one script |
| D-056 | A document needing three or more judge windows gets one whole-document assessment from a long-context model (role `judge_long`); the windows remain the fallback | One call instead of many (3–7 s for 30K–300K characters measured); long real pages are no longer held |
| D-057 | **Not adopted**: judging every user message with a dedicated user-turn prompt. On the development set it caught 17 of 60 user-turn attacks the classifier missed and flagged 4 of 20 ordinary user tasks | The cost to real users outweighs the gain; user-turn detection stays a known limitation |

## Actions and sessions

| # | Decision | Why |
|---|---|---|
| D-039 | Allow-lists parse URLs and email addresses the way real clients do (fragments, user parts, backslashes, display names); a classifier failure sends every chunk to the judge; agents without a policy are refused; bounded in-process state | Each of these was a verified bypass |
| D-042 | **Data-flow tracing**: per-session origin fingerprints of untrusted content; tool arguments are traced to their origins; text from flagged content copied into a high-risk tool is escalated | Extends provenance from recipients and URLs to any argument |
| D-053 | Session risk from third-party content gates actions and further documents; the user's own messages are held only for risk built by the user's turns | A poisoned document must not lock the user out of their own conversation; multi-step attacks by the user are still caught |
| D-055 | **Answer check**: the model's final answer is scanned like a tool argument (canaries, registered secrets, secret formats, also encoded): redacted, or withheld when it cannot be; streamed answers are held back by twice the longest protected value and scanned before release | Secrets can leave through the answer as well as through tools |

## Integration

| # | Decision | Why |
|---|---|---|
| D-003 | Providers and models live in `config/providers.yaml` and `config/models.yaml`; nothing provider-specific in logic | Model lineups change often |
| D-004 | One key per provider is used; extra keys are spares used only when the active key is rejected. A rate limit cools the provider down and the router fails over to the next provider, never to another account's key | Multiplying rate limits with extra accounts would breach provider terms |
| D-028 | Proxy: the agent is named in the URL and sessions come from a conversation fingerprint (or `X-Session-Id`), so an unmodified OpenAI-SDK agent is protected by its base URL alone; each message is inspected once per session | Stateless clients resend the whole history every turn |
| D-040 | Proxy streaming: text streams through; tool-call deltas are buffered, assembled, checked, then released or replaced by a notice; a mid-stream failure never releases a partial call | A tool call must be checked whole |
| D-043 | Organisations: keys and policies carry an organisation and an optional agent list; every agent-scoped read is limited to the key's agents | One gateway can serve several teams without sharing evidence |
| D-044 | PostgreSQL (optional) behind one portable SQL dialect; SIEM records in ECS-style JSON Lines and CEF, pull or push through a bounded queue that never blocks a decision | Standard formats every SIEM ingests |
| D-048 | Any major provider: native Anthropic adapter and Messages-API proxy; per-agent `upstream` (provider, model, the gateway's key or the client's own key, never stored) | Deployments keep their own model and key |
| D-049 | Onboarding: Console Set up and API, policy templates, connection snippets, a self-test with structural probes; new agents start in monitor mode | Teams measure false alarms before enforcing |
| D-050 | **RAG and inline files through the proxy**: text inside `<context>`/`<document>` (and similar) tags in a system or user message is inspected as untrusted retrieved content; the user's own words are checked first; inline images and PDFs are extracted and OCR-inspected | Retrieved documents are third-party content wherever an app places them |
| D-052 | PyPI: `intentseal` (SDK) and `intentseal-core` (engine); light install for remote mode, engine behind `[embedded]`; bundled configuration; `intentseal init`; trusted publishing | Apps that use a gateway should not install the whole engine |

## Operations and evaluation

| # | Decision | Why |
|---|---|---|
| D-025 / D-029 | False-alarm rate is reported on a **held-out** hard-benign set written before any tuning, each case in its own channel (an email as an email) | Honest false-alarm numbers |
| D-031 / D-035 | Channel and encoding pairs a channel cannot deliver (for example long base64 through OCR) are reported separately and excluded from the claim | Those cases test the fixture, not the firewall |
| D-033 | Cost overhead is measured per protected run: security tokens and cost against the agent's own tokens and cost in the same session | A meaningful overhead number |
| D-034 | Multi-step evidence from generated user-turn attacks split over 2–3 consecutive turns, scored at the session checkpoint | Multi-step attacks need multi-turn cases |
| D-037 | Console reviewer actions require the reviewer's own admin key, held for the browser tab only; the public key stays read-only | Approvals and policy edits without weakening the public view |
| D-045 | Container defaults: classifier baked in, non-root user, `/data` volume, content previews off, one worker, trusted proxies only, readiness-gated health check | Secure and predictable by default |
| D-046 | Every reported number comes from one orchestrated run on one engine fingerprint (`eval/run_final.sh`) | No mixing of results from different engine versions |
