"""Tier 1 classifiers (CORE-4): cheap signals that decide what to escalate, never final decisions (D-011).

- LocalClassifier: protectai/deberta-v3-base-prompt-injection-v2 (Apache-2.0), ONNX on CPU, chunked.
- RemoteGuard: Llama Prompt Guard 2 via the router role `tier1_remote` (hosted, free tier).
Both cache by content hash (CC2).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from functools import lru_cache
from pathlib import Path

from .config import repo_root

log = logging.getLogger("asg.tier1")
MODEL_REPO = os.environ.get("ASG_TIER1_MODEL", "protectai/deberta-v3-base-prompt-injection-v2")


class LocalClassifier:
    def __init__(self, repo: str = MODEL_REPO, threads: int | None = None) -> None:
        import numpy as np  # noqa: F401  (import check)
        import onnxruntime as ort
        from huggingface_hub import snapshot_download
        from tokenizers import Tokenizer

        os.environ.setdefault("HF_HOME", str(repo_root() / "data" / "hf_cache"))
        path = Path(snapshot_download(repo, allow_patterns=["onnx/*", "*.json"]))
        tok = path / "onnx" / "tokenizer.json"
        self.tok = Tokenizer.from_file(str(tok if tok.exists() else path / "tokenizer.json"))
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or int(os.environ.get("ASG_TIER1_THREADS") or "2")
        self.sess = ort.InferenceSession(str(path / "onnx" / "model.onnx"), so, providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        cfg = json.loads((path / "config.json").read_text())
        self.pos = next(int(k) for k, v in cfg["id2label"].items() if "INJ" in v.upper())
        self.cls, self.sep = self.tok.token_to_id("[CLS]"), self.tok.token_to_id("[SEP]")
        self._lock = threading.Lock()
        self._cache: dict[str, float] = {}

    def score(self, text: str) -> float:
        """Max probability over windows of up to 256 tokens (shorter windows keep CPU latency low)."""
        import numpy as np

        key = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
        if key in self._cache:
            return self._cache[key]
        ids = self.tok.encode(text, add_special_tokens=False).ids
        best, window, stride = 0.0, 254, 200
        with self._lock:
            for start in range(0, max(1, len(ids)), stride):
                chunk = [self.cls] + ids[start:start + window] + [self.sep]
                feed = {"input_ids": np.array([chunk], dtype=np.int64),
                        "attention_mask": np.ones((1, len(chunk)), dtype=np.int64)}
                if "token_type_ids" in self.inputs:
                    feed["token_type_ids"] = np.zeros((1, len(chunk)), dtype=np.int64)
                logits = self.sess.run(None, feed)[0][0]
                p = np.exp(logits - logits.max())
                best = max(best, float((p / p.sum())[self.pos]))
                if start + window >= len(ids):
                    break
        self._cache[key] = best
        return best


@lru_cache(maxsize=1)
def local_classifier() -> LocalClassifier | None:
    try:
        return LocalClassifier()
    except Exception as e:  # missing model / runtime: engine runs degraded, never fails open silently
        log.warning("Tier 1 local classifier unavailable: %s", type(e).__name__)
        return None


class RemoteGuard:
    """Prompt Guard 2 via the router (role `tier1_remote`). Returns None when unavailable."""

    def __init__(self, router, role: str = "tier1_remote") -> None:
        self.router = router
        self.role = role
        self._cache: dict[str, float] = {}

    async def score(self, text: str) -> float | None:
        from .llm.adapters import ChatRequest
        from .llm.router import AllProvidersFailed

        if self.role not in self.router.settings.roles:
            return None
        key = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()
        if key in self._cache:
            return self._cache[key]
        try:
            r = await self.router.chat(self.role, ChatRequest(messages=[{"role": "user", "content": text[:2000]}],
                                                              max_tokens=8, temperature=None))
            val = float((r.content or "").strip())
        except (AllProvidersFailed, ValueError):
            return None
        self._cache[key] = val
        return val
