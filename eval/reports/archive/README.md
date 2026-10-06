# Superseded reports (5 Oct 2026)

First-day reports, kept for the record. **Do not quote these numbers.** They predate:

- DEF-019: a same-site `http://` fetch was counted as an external fetch (inflated attack success);
- the v2 corpus (every indirect payload through every channel), the held-out benign set and the §15 claim rule;
- excluding fail-safe holds from scoring and stamping results with an engine fingerprint (DEF-021).

The current figures are in `docs/EVALUATION.md`, generated from `eval/reports/<date>-summary.json`
(`python -m asg_eval.summary`). The summary re-scores these suites' raw outputs exactly with the current rules.
