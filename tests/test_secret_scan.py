"""Public model attribution must be publishable while opaque credentials stay blocked."""
import importlib.util
from pathlib import Path


def scanner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "secret_scan.py"
    spec = importlib.util.spec_from_file_location("traceverdict_secret_scan", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_route_and_opaque_credentials(tmp_path, monkeypatch, capsys):
    scan = scanner()
    monkeypatch.setattr(scan, "ROOT", tmp_path)
    token = "opaque-runtime-credential-for-test-only"
    route = "nvidia/nemotron-test-model"
    (tmp_path / ".env").write_text(f'METERLESS_MODEL="{route}"\nMETERLESS_REPLAY_MODEL="{route}"\nMETERLESS_RUNTIME_TOKEN="{token}"\n')
    report = tmp_path / "report.txt"
    report.write_text(route)
    assert scan.main([report.name]) == 0
    report.write_text(token)
    assert scan.main([report.name]) == 1
    assert token not in capsys.readouterr().out
    report.write_text("nvapi-" + "x" * 40)
    assert scan.main([report.name]) == 1


def test_non_route_model_setting_is_still_scanned(tmp_path, monkeypatch):
    scan = scanner()
    monkeypatch.setattr(scan, "ROOT", tmp_path)
    value = "opaque-private-setting-for-test"
    (tmp_path / ".env").write_text(f"METERLESS_MODEL={value}\n")
    (tmp_path / "report.txt").write_text(value)
    assert scan.main(["report.txt"]) == 1
