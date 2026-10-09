# Contributing to IntentSeal

Thanks for helping make AI agents safer. Bug reports, false-alarm reports, new integrations, documentation and
evaluation improvements are all welcome.

## Ways to contribute

- **Report a bug or a false alarm**: open an issue with the template. For a false alarm, include the input type
  (web page, PDF, email, ...), the decision and rule shown in the Console or the SDK result, and a minimal benign
  example if you can share one.
- **Report a missed attack**: if it is a vulnerability in IntentSeal itself (a bypass of the action guard, an
  authentication or tenancy issue, a way to read other agents' data), follow [SECURITY.md](SECURITY.md) instead of
  opening a public issue.
- **Add an integration**: a framework helper, a proxy format, a provider adapter or a policy template.
- **Improve the evaluation**: new benign hard cases, new channels, better scoring.

## Development setup

Python 3.11 or newer, Node 20+ for the Console.

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.lock      # .venv/bin on Linux and macOS
.venv/Scripts/pip install --no-deps -e packages/core -e packages/sdk -e agents -e services/gateway -e eval
cp .env.example .env
.venv/Scripts/python -m pytest -q
```

The test suite runs offline (model providers are mocked). Storage tests also run on PostgreSQL when
`INTENTSEAL_TEST_DATABASE_URL` is set.

## Before you open a pull request

```bash
.venv/Scripts/python -m ruff check .                    # lint (correctness rules)
.venv/Scripts/python -m pytest -q                       # tests
.venv/Scripts/python scripts/secret_scan.py --all       # no keys in the repository
.venv/Scripts/python scripts/sync_package_data.py       # if you changed config/: refresh the packaged copies
```

- Keep changes focused, with a test for every behaviour change. Engine decisions must stay deterministic given the
  same inputs and model answers.
- Never commit provider keys, real customer data or real secrets; use the test canaries in the fixtures.
- Attack test cases come from generators (promptfoo, garak) or public research datasets with a compatible licence;
  please do not add new hand-written attack payloads. Benign cases are welcome.
- Changes that alter decisions should say what they change and, if possible, include evaluation numbers before and
  after (`eval/run_final.sh`).
- Larger design changes: open an issue first; significant choices are recorded in
  [docs/DECISIONS.md](docs/DECISIONS.md).

## Code style

Python: type hints, small functions, docstrings that explain why. Comments describe behaviour, not history.
Console: TypeScript, React, existing components and design tokens.

By contributing you agree that your contributions are licensed under the Apache License 2.0, and you agree to follow
the [Code of Conduct](CODE_OF_CONDUCT.md).
