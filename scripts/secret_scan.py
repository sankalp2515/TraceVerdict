"""Pre-commit secret scan. Blocks a commit if a staged file contains a provider-key-shaped string
or any value currently set in .env. Prints file and line only, never the matched value.

Install: python scripts/install_hooks.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),
    re.compile(r"sk-or-v1-[A-Za-z0-9]{20,}"),
    re.compile(r"nvapi-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{32,}"),
    re.compile(r"hf_[A-Za-z0-9]{30,}"),
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def env_values() -> list[str]:
    env = ROOT / ".env"
    if not env.exists():
        return []
    vals = []
    for line in env.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            if len(v) >= 12:
                vals.append(v)
    return vals


def staged_files() -> list[str]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, cwd=ROOT, check=True).stdout
    return [f for f in out.splitlines() if f]


def main(files: list[str] | None = None) -> int:
    files = files if files is not None else staged_files()
    values = env_values()
    hits = 0
    for f in files:
        if Path(f).name == ".env":
            print(f"BLOCKED: {f} must never be committed")
            hits += 1
            continue
        try:
            text = (ROOT / f).read_text(encoding="utf-8", errors="ignore")
        except (FileNotFoundError, IsADirectoryError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if any(p.search(line) for p in PATTERNS) or any(v in line for v in values):
                print(f"BLOCKED: possible secret in {f}:{n}")
                hits += 1
    if hits:
        print("Commit blocked by secret scan. Remove the secret (use env vars) and try again.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or None))
