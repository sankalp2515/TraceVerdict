"""PyPI packaging (E4): bundled defaults in sync with config/, a light remote-mode SDK, `intentseal init` for an
installed package (no source checkout)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_bundled_package_data_matches_config():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "sync_package_data.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + "\nrun: python scripts/sync_package_data.py"


def test_remote_mode_imports_no_engine_libraries():
    code = ("import sys, intentseal, intentseal.remote\n"
            "heavy = [m for m in ('bs4', 'pdfplumber', 'pypdf', 'docx', 'detect_secrets', 'ftfy', 'onnxruntime',"
            " 'intentseal_core.engine') if m in sys.modules]\n"
            "print(','.join(heavy))")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert r.stdout.strip() == "", f"remote mode should not load: {r.stdout.strip()}"


def test_installed_package_uses_a_user_home_and_bundled_config(tmp_path, monkeypatch):
    from intentseal_core import cli, config

    monkeypatch.setenv("INTENTSEAL_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("INTENTSEAL_POLICY_DIR", raising=False)
    assert config.config_path("providers.yaml") == config.DEFAULTS / "providers.yaml"    # nothing in the home yet
    assert config.load_providers() and config.load_roles()
    assert cli.main(["init", "--agent", "support-bot", "--template", "customer-support"]) == 0
    policy = yaml.safe_load((tmp_path / "home" / "policies" / "support-bot.yaml").read_text(encoding="utf-8"))
    assert policy["agent"] == "support-bot" and policy["mode"] == "enforce" and "issue_refund" in policy["tools"]
    assert (tmp_path / "home" / ".env").exists()
    assert cli.main(["init", "--agent", "support-bot"]) == 1                              # never overwrites
    assert cli.main(["init", "--agent", "../x"]) == 2


def test_wheels_carry_the_package_data():
    import tomllib

    core = tomllib.loads((ROOT / "packages" / "core" / "pyproject.toml").read_text(encoding="utf-8"))
    data = core["tool"]["setuptools"]["package-data"]["intentseal_core"]
    for pattern in data:
        assert list((ROOT / "packages" / "core" / "intentseal_core").glob(pattern)), pattern
    sdk = tomllib.loads((ROOT / "packages" / "sdk" / "pyproject.toml").read_text(encoding="utf-8"))
    assert f"intentseal-core=={core['project']['version']}" in sdk["project"]["dependencies"]
    assert sdk["project"]["version"] == core["project"]["version"]
