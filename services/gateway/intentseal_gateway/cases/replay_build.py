"""Fingerprint the local replay implementation alongside immutable task inputs."""
from pathlib import Path
import intentseal_core.action_guard as guard
import intentseal_core.contract as contract
import intentseal_core.policy as policy
import intentseal_core.session as session

from .models import digest


def replay_build_sha256():
    paths = [Path(__file__), Path(__file__).with_name("agent_replay.py"), Path(__file__).with_name("replay.py"),
             *[Path(m.__file__) for m in (guard, contract, policy, session)]]
    # Text normalization keeps Windows and the Linux image reproducible.
    return digest({p.name: p.read_text(encoding="utf-8").replace("\r\n", "\n") for p in paths})
