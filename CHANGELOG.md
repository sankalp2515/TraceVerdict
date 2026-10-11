# Changelog

All notable changes to IntentSeal. Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `docker compose up` runs the whole system on one machine: gateway, LLM proxy, the Security Console (now served by
  the gateway at `/`) and the test assistant with sample files and a labelled attack test pack.
- LLM proxy: `GET /proxy/<agent>/v1/models` for clients that discover models first (agent frameworks, chat UIs).
- Policies for the test assistant (`my-assistant`) and for Hermes Agent connected through the proxy (`hermes`).
- **Intent contracts** (D-064): a versioned, hash-chained contract per session, compiled from the user's own words and
  the policy; tool calls the user prohibited are blocked and unrequested high-impact calls held. `POST /v1/sessions`
  returns it, `GET /v1/sessions/{id}/contract` lists its versions, and every action decision records the deciding
  clause. Policy: `contract: {mode: enforce}`; tool `capability`.
- **Attack-to-action provenance and execution receipts** (D-065): `GET /v1/sessions/{id}/provenance`,
  `POST /v1/actions/{id}/receipt`, `Guard.record_execution` (automatic in `@guard.tool`); Console Replay shows the chain
  and the contract.
- Evaluation: `content_checks: observe` (detectors bypassed) and the `actions` protection arm; paired comparisons with
  Wilson intervals and repeated trials (`intentseal_eval.paired`); deterministic contract evaluation
  (`intentseal_eval.contract_eval`); the red-team and repair loop (`intentseal_eval.redteam`); `docs/ASSURANCE.md`.
- `examples/node-rest/agent.mjs`: IntentSeal from Node over REST, with the check at the tool-execution boundary.
- Playground scenario S10: detectors off, the intent contract stops the send.

### Fixed
- Empty key placeholders written by `intentseal init` no longer hide a key set in the project's own `.env`.

## [0.1.0] - 2026-10-09

First public release.

### Added
- Core engine: extraction for text, Markdown, HTML, PDF, Word, email, JSON, source code and images (OCR), with
  hidden-text surfacing; normalisation and decoding (look-alike letters, base64, hex, %-encoding, Unicode tags,
  rot13); tiered detection (known-attack memory and structural rules, local classifier, AI judge, long-context judge
  for long documents); per-agent deterministic policy; session risk; data-flow tracing; decision log with redaction.
- Action guard: tool, recipient, domain and path allow-lists, pinned fields, outbound secret scan (also encoded),
  explicit-intent rule for high-risk actions, provenance and taint checks, human approvals.
- Answer check: protected data in the model's final answer is redacted or withheld (proxy, SDK, REST).
- Python SDK (`intentseal`): embedded or remote mode, tool decorator, LangChain/LangGraph helper, `intentseal init`.
- Gateway: REST API, LLM proxy in the OpenAI, Anthropic and Gemini formats with streaming, RAG context and inline files,
  onboarding API and policy templates, organisations, PostgreSQL, SIEM export (JSON Lines, CEF), Docker image.
- Security Console: overview, decisions, review and approvals, session replay, policy, set up.
- Evaluation harness with promptfoo and garak, hard benign sets, generated reports.
