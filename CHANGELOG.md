# Changelog

All notable changes to IntentSeal. Versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-10

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
- Gateway: REST API, OpenAI- and Anthropic-compatible LLM proxy with streaming, RAG context and inline files,
  onboarding API and policy templates, organisations, PostgreSQL, SIEM export (JSON Lines, CEF), Docker image.
- Security Console: overview, decisions, review and approvals, session replay, policy, set up.
- Evaluation harness with promptfoo and garak, hard benign sets, generated reports.
