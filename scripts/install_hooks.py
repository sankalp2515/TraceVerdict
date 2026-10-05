"""Install the git pre-commit hook that runs the secret scan."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
hook = ROOT / ".git" / "hooks" / "pre-commit"
hook.write_text(
    "#!/bin/sh\n"
    'PY="$(git rev-parse --show-toplevel)/.venv/Scripts/python"\n'
    '[ -x "$PY" ] || PY="$(git rev-parse --show-toplevel)/.venv/bin/python"\n'
    '[ -x "$PY" ] || PY=python3\n'
    'exec "$PY" "$(git rev-parse --show-toplevel)/scripts/secret_scan.py"\n',
    newline="\n",
)
hook.chmod(0o755)
print(f"installed {hook}")
