# Security policy

IntentSeal is a security product, so we take reports about it seriously.

## Reporting a vulnerability

Please **do not open a public issue** for a vulnerability. Use GitHub's private reporting
([Security → Report a vulnerability](https://github.com/sankalp2515/intentseal/security/advisories/new)) or email
sankalpwanjari85@gmail.com with:

- what is affected (engine, SDK, gateway API, proxy, Console) and the version or commit;
- steps to reproduce, and the impact you observed;
- whether the issue is already public.

You will get an acknowledgement within 3 working days and a status update within 10. Fixes are released as a new
version with a security note in the [changelog](CHANGELOG.md); reporters are credited if they wish.

## In scope

- Bypasses of the deterministic checks: tool, recipient, domain or path allow-lists; pinned fields; the outbound
  secret scan; approvals.
- Authentication, key scopes and organisation isolation in the gateway; reading another agent's evidence.
- Content that is passed to the model unchecked when it should have been inspected (a channel or format that skips
  inspection, a fail-open path).
- Leaks of keys, canaries or redacted content into logs, the decision store or SIEM exports.

## Out of scope

- A single attack text that the detectors miss while the action guard still stops the harmful action: please report
  it as a regular issue (a missed detection), it helps the evaluation.
- Attacks that need the operator's own admin key or access to the host.
- Findings in third-party models or providers.

## Supported versions

Security fixes go to the latest released version.
