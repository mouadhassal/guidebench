"""Minimal Ollama client with an on-disk cache, so interrupted runs resume for free."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

HOST = "http://localhost:11434"
CACHE = Path(__file__).resolve().parents[2] / ".cache" / "llm"


def _key(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def chat(model: str, messages: list[dict], schema: dict | None = None, *,
         temperature: float = 0.0, seed: int = 7, num_ctx: int = 6144,
         num_predict: int = 700) -> dict:
    """Returns {"content", "seconds", "prompt_tokens", "output_tokens", "cached"}."""
    body = {
        "model": model, "messages": messages, "stream": False, "think": False,
        "options": {"temperature": temperature, "seed": seed, "num_ctx": num_ctx,
                    "num_predict": num_predict},
    }
    if schema is not None:
        body["format"] = schema
    path = CACHE / f"{_key(body)}.json"
    if path.exists():
        out = json.loads(path.read_text(encoding="utf-8"))
        out["cached"] = True
        return out
    t0 = time.perf_counter()
    for attempt in range(4):
        try:
            r = requests.post(f"{HOST}/api/chat", json=body, timeout=600)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    d = r.json()
    out = {
        "content": d["message"]["content"],
        "seconds": time.perf_counter() - t0,
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "output_tokens": d.get("eval_count", 0),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    out["cached"] = False
    return out


def embed(model: str, texts: list[str]) -> list[list[float]]:
    # On this GPU, Ollama's F16 bge-m3 returns NaN for some inputs; CPU is exact.
    body = {"model": model, "input": texts, "options": {"num_gpu": 0}}
    path = CACHE / f"emb_{_key(body)}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    e = []
    for i in range(0, len(texts), 8):
        part = {**body, "input": texts[i:i + 8]}
        for attempt in range(4):
            r = requests.post(f"{HOST}/api/embed", json=part, timeout=600)
            if r.ok:
                break
            if attempt == 3:
                r.raise_for_status()
            time.sleep(3 * (attempt + 1))
        e += r.json()["embeddings"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(e), encoding="utf-8")
    return e
