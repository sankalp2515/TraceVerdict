"""Validate A2: do local/open classifiers catch attacks with acceptable false alarms?

Classifiers:
  - protectai/deberta-v3-base-prompt-injection-v2 (Apache-2.0), local ONNX on CPU, sliding window.
  - meta-llama/llama-prompt-guard-2-86m via Groq API (Llama 4 Community licence; hosted, free tier).
Sample (labels from the datasets; text never printed):
  attacks: deepset test (Apache-2.0), neuralchemy test (Apache-2.0), LLMail-Inject successful emails (MIT),
           Lakera Gandalf (MIT)
  benign:  deepset test, neuralchemy test, jackhhao test (Apache-2.0), our hard-benign set
Writes eval/validate/results/a2.json.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("HF_HOME", str(ROOT / "data" / "hf_cache"))
logging.getLogger("httpx").setLevel(logging.WARNING)


class OnnxClassifier:
    def __init__(self, repo: str = "protectai/deberta-v3-base-prompt-injection-v2") -> None:
        import onnxruntime as ort
        from huggingface_hub import snapshot_download
        from tokenizers import Tokenizer
        path = Path(snapshot_download(repo, allow_patterns=["onnx/*", "*.json"]))
        tok_file = path / "onnx" / "tokenizer.json"
        self.tok = Tokenizer.from_file(str(tok_file if tok_file.exists() else path / "tokenizer.json"))
        self.sess = ort.InferenceSession(str(path / "onnx" / "model.onnx"), providers=["CPUExecutionProvider"])
        self.inputs = {i.name for i in self.sess.get_inputs()}
        cfg = json.loads((path / "config.json").read_text())
        self.inj_index = next(int(k) for k, v in cfg["id2label"].items() if "INJ" in v.upper())

    def score(self, text: str, window: int = 510, stride: int = 384) -> float:
        ids = self.tok.encode(text, add_special_tokens=False).ids
        cls, sep = self.tok.token_to_id("[CLS]"), self.tok.token_to_id("[SEP]")
        best = 0.0
        for start in range(0, max(1, len(ids)), stride):
            chunk = [cls] + ids[start:start + window] + [sep]
            feed = {"input_ids": np.array([chunk], dtype=np.int64),
                    "attention_mask": np.ones((1, len(chunk)), dtype=np.int64)}
            if "token_type_ids" in self.inputs:
                feed["token_type_ids"] = np.zeros((1, len(chunk)), dtype=np.int64)
            logits = self.sess.run(None, feed)[0][0]
            p = np.exp(logits - logits.max()); p /= p.sum()
            best = max(best, float(p[self.inj_index]))
            if start + window >= len(ids):
                break
        return best


def build_sample(seed: int = 11) -> list[dict]:
    from datasets import load_dataset
    rng = random.Random(seed)
    out: list[dict] = []

    def take(rows, n, label, src):
        for r in rng.sample(rows, min(n, len(rows))):
            out.append({"text": r, "label": label, "src": src})

    ds = load_dataset("deepset/prompt-injections", split="test")
    take([r["text"] for r in ds if r["label"] == 1], 15, 1, "deepset")
    take([r["text"] for r in ds if r["label"] == 0], 15, 0, "deepset")
    nc = load_dataset("neuralchemy/Prompt-injection-dataset", split="test")
    for cat, n in [("direct_injection", 6), ("jailbreak", 5), ("encoding", 6), ("adversarial", 3), ("agent_manipulation", 3), ("training_extraction", 3)]:
        take([r["text"] for r in nc if r["category"] == cat and r["label"] == 1], n, 1, f"neuralchemy:{cat}")
    take([r["text"] for r in nc if r["label"] == 0], 15, 0, "neuralchemy:benign")
    ll = load_dataset("microsoft/llmail-inject-challenge", split="Phase1")
    idx = [i for i, o in enumerate(ll["objectives"]) if all(json.loads(o).get(k) for k in ("exfil.sent", "exfil.destination", "exfil.content"))]
    take([(ll[i]["subject"] or "") + "\n" + (ll[i]["body"] or "") for i in rng.sample(idx, 200)], 15, 1, "llmail")
    g = load_dataset("Lakera/gandalf_ignore_instructions", split="test")
    take([r["text"] for r in g], 10, 1, "gandalf")
    jh = load_dataset("jackhhao/jailbreak-classification", split="test")
    take([r["prompt"] for r in jh if r["type"] == "benign"], 10, 0, "jackhhao:benign")
    hb = yaml.safe_load((ROOT / "eval/corpus/v0/hard_benign.yaml").read_text(encoding="utf-8"))["cases"]
    out += [{"text": c["text"], "label": 0, "src": "hard_benign"} for c in hb]
    return out


async def prompt_guard_scores(texts: list[str]) -> list[float | None]:
    from intentseal_core.llm.adapters import ChatRequest, ProviderError
    from intentseal_core.llm.router import Router
    router = Router()
    scores: list[float | None] = []
    for t in texts:
        try:
            r = await router.call_direct("groq", "meta-llama/llama-prompt-guard-2-86m",
                                         ChatRequest(messages=[{"role": "user", "content": t[:4000]}], max_tokens=10, temperature=None),
                                         role="validate")
            scores.append(float((r.content or "").strip()))
        except (ProviderError, ValueError):
            scores.append(None)
    await router.aclose()
    return scores


def metrics(items: list[dict], key: str, thr: float) -> dict:
    xs = [i for i in items if i.get(key) is not None]
    atk = [i for i in xs if i["label"] == 1]
    ben = [i for i in xs if i["label"] == 0]
    recall = sum(i[key] >= thr for i in atk) / max(1, len(atk))
    fpr = sum(i[key] >= thr for i in ben) / max(1, len(ben))
    hb = [i for i in ben if i["src"] == "hard_benign"]
    by_src: dict[str, list] = {}
    for i in atk:
        by_src.setdefault(i["src"], []).append(i[key] >= thr)
    return {"threshold": thr, "n_attack": len(atk), "n_benign": len(ben), "recall": round(recall, 3),
            "fpr": round(fpr, 3), "fpr_hard_benign": round(sum(i[key] >= thr for i in hb) / max(1, len(hb)), 3),
            "recall_by_source": {k: round(sum(v) / len(v), 2) for k, v in sorted(by_src.items())}}


def main() -> None:
    sample = build_sample()
    t0 = time.perf_counter()
    clf = OnnxClassifier()
    load_s = time.perf_counter() - t0
    lat = []
    for it in sample:
        t = time.perf_counter()
        it["protectai"] = clf.score(it["text"])
        lat.append((time.perf_counter() - t) * 1000)
    pg = asyncio.run(prompt_guard_scores([i["text"] for i in sample]))
    for it, s in zip(sample, pg):
        it["prompt_guard"] = s
    for it in sample:
        a, b = it["protectai"], it["prompt_guard"]
        it["either"] = max(a, b if b is not None else 0.0)
    res = {
        "n": len(sample), "model_load_s": round(load_s, 1),
        "protectai_latency_ms": {"p50": round(float(np.percentile(lat, 50)), 1), "p95": round(float(np.percentile(lat, 95)), 1)},
        "protectai": [metrics(sample, "protectai", t) for t in (0.5, 0.9)],
        "prompt_guard_groq": [metrics(sample, "prompt_guard", t) for t in (0.5, 0.9)],
        "either": [metrics(sample, "either", t) for t in (0.5, 0.9)],
        "prompt_guard_errors": sum(s is None for s in pg),
    }
    print(json.dumps(res, indent=1))
    out = Path(__file__).parent / "results" / "a2.json"
    out.write_text(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
