"""Turn a generated red-team test file into a plain promptfoo eval scored only by our deterministic
assertion (EVAL-5). promptfoo's hosted red-team graders are not used.

Usage: python to_plain_eval.py output/<name>.tests.yaml  -> output/<name>.plain.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


def main(path: str) -> None:
    src = Path(path)
    cfg = yaml.safe_load(src.read_text(encoding="utf-8"))
    cfg.pop("redteam", None)
    for t in cfg.get("tests", []):
        t["assert"] = [a for a in t.get("assert", []) if not str(a.get("type", "")).startswith("promptfoo:redteam")]
        t.setdefault("options", {}).pop("provider", None)
    dst = src.with_name(src.name.replace(".tests.yaml", ".plain.yaml"))
    dst.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True), encoding="utf-8")
    print(dst)


if __name__ == "__main__":
    main(sys.argv[1])
