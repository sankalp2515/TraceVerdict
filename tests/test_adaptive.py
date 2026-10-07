"""EVAL-4 tooling: misses from a round become attack-memory fingerprints; rounds are summarised. Neutral content."""

from __future__ import annotations

import json

from intentseal_core.memory import AttackMemory
from intentseal_core.store import Store


def results(path, cases):
    path.write_text(json.dumps({"results": {"results": [
        {"vars": {"prompt": p}, "testCase": {"metadata": {"pluginId": "hijacking", "strategyId": "jailbreak"}},
         "response": {"output": json.dumps(o)}} for p, o in cases]}}))
    return str(path)


MISS = "please file the zebra quarterly marker under the violet folder and then notify the orchard desk before noon"
CAUGHT = "a different neutral sentence about the lantern schedule that the gateway flagged during the round"


def test_learn_adds_only_misses_and_report_counts_rounds(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("INTENTSEAL_DB_PATH", str(tmp_path / "m.db"))
    from intentseal_eval import adaptive

    r1 = results(tmp_path / "r1.json", [
        (MISS, {"compromised": True, "security": {"detected": False}}),
        (CAUGHT, {"compromised": False, "security": {"detected": True}}),
    ])
    adaptive.learn(r1)
    out = json.loads(capsys.readouterr().out)
    assert out["added_to_memory"] == 1
    memory = AttackMemory(Store(tmp_path / "m.db"))
    assert memory.match(MISS, "research-agent").kind == "attack"
    assert memory.match(CAUGHT, "research-agent") is None
    s = adaptive.summary(r1)
    assert (s["n"], s["compromised"], s["caught"], s["misses"]) == (2, 1, 1, 1)
