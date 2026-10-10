"""Run one condition over a set of products and languages; writes one JSONL row per conversation.

    python -m guidebench.run --products invoxa parcelo --model qwen3:8b --retrieval bm25 [--guard]
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from .agent import Agent, Config
from .kb import ROOT, load_kb

LANGS = ["en", "et", "lt", "ru", "fr", "de", "ar"]


def personas(key: str) -> list[dict]:
    return json.loads((ROOT / "personas" / f"{key}.json").read_text(encoding="utf-8"))["personas"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", nargs="+", default=["invoxa", "parcelo"])
    ap.add_argument("--langs", nargs="+", default=LANGS)
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--retrieval", default="bm25", choices=["bm25", "dense", "oracle"])
    ap.add_argument("--guard", action="store_true")
    ap.add_argument("--only", nargs="*", help="persona ids")
    ap.add_argument("--out", default="results/runs")
    a = ap.parse_args(argv)
    cfg = Config(a.model, a.retrieval, a.guard)
    out = ROOT / a.out / f"{cfg.name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            done.add((r["persona"], r["lang"]))
    t0 = time.time()
    n = 0
    with out.open("a", encoding="utf-8") as f:
        for key in a.products:
            agent = Agent(load_kb(key), cfg)
            for p in personas(key):
                if a.only and p["id"] not in a.only:
                    continue
                for lang in a.langs:
                    if (p["id"], lang) in done or lang not in p["turns"][0]["text"]:
                        continue
                    turns = agent.run(p["turns"], lang)
                    f.write(json.dumps({"condition": cfg.name, "product": key, "persona": p["id"],
                                        "archetype": p["archetype"], "gold": p["gold"], "lang": lang,
                                        "turns": turns}, ensure_ascii=False) + "\n")
                    f.flush()
                    n += 1
                    print(f"[{cfg.name}] {p['id']} {lang} done ({n}, {time.time() - t0:.0f}s)", flush=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
