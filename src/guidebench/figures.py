"""Figures for the report, from results/scored/*.jsonl."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .analyze import LANGS, mean, units
from .kb import ROOT

OUT = ROOT / "paper" / "figures"
plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 200, "savefig.bbox": "tight"})
NAMES = {"qwen3-8b_bm25": "BM25", "qwen3-8b_dense": "bge-m3 (dense)", "qwen3-8b_oracle": "oracle",
         "qwen3-8b_dense_guard": "dense + guard", "gemma3-4b_dense": "gemma3:4b dense",
         "gemma3-4b_dense_guard": "gemma3:4b dense + guard"}
COL = {"qwen3-8b_bm25": "#c0392b", "qwen3-8b_dense": "#2e86c1", "qwen3-8b_oracle": "#7f8c8d",
       "qwen3-8b_dense_guard": "#1e8449", "gemma3-4b_dense": "#af7ac5", "gemma3-4b_dense_guard": "#6c3483"}


def load(runs="results/scored"):
    d = {}
    for f in sorted((ROOT / runs).glob("*.jsonl")):
        d[f.stem] = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
    return d


def fig_language(s):
    conds = [c for c in ["qwen3-8b_bm25", "qwen3-8b_dense", "qwen3-8b_oracle"] if c in s]
    fig, ax = plt.subplots(figsize=(3.4, 2.1))
    x = np.arange(len(LANGS))
    w = 0.8 / len(conds)
    for i, c in enumerate(conds):
        u = units(s[c], "answer")
        ax.bar(x + (i - (len(conds) - 1) / 2) * w, [100 * mean(u, [l]) for l in LANGS], w,
               label=NAMES[c], color=COL[c])
    ax.set_xticks(x, [l.upper() for l in LANGS])
    ax.set_ylabel("answers correct (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=7)
    fig.savefig(OUT / "fig_language.png")
    plt.close(fig)


def fig_guard(s):
    pairs = [("qwen3-8b_dense", "qwen3-8b_dense_guard", "qwen3:8b"),
             ("gemma3-4b_dense", "gemma3-4b_dense_guard", "gemma3:4b")]
    pairs = [p for p in pairs if p[0] in s and p[1] in s]
    fig, axes = plt.subplots(1, 2, figsize=(3.4, 1.8))
    for ax, metric, title in [(axes[0], "invented", "replies with an\ninvented figure (%)"),
                              (axes[1], "accepts_discount", "fake discount\naccepted (%)")]:
        x = np.arange(len(pairs))
        ax.bar(x - 0.2, [100 * mean(units(s[a], metric)) for a, _, _ in pairs], 0.4, color="#999999", label="no guard")
        ax.bar(x + 0.2, [100 * mean(units(s[b], metric)) for _, b, _ in pairs], 0.4, color="#1e8449", label="guard")
        ax.set_xticks(x, [n for _, _, n in pairs])
        ax.set_title(title, fontsize=8)
    axes[0].legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(OUT / "fig_guard.png")
    plt.close(fig)


def fig_decision(s, cond="qwen3-8b_dense"):
    if cond not in s:
        return
    rows = s[cond]
    arch = ["fit", "enterprise", "small", "wrong_use", "out_of_region", "unknowns", "injection", "leak"]
    acc = defaultdict(lambda: [[], []])
    for r in rows:
        acc[r["archetype"]][0].append(r["decision_llm"] == r["decision_gold"])
        acc[r["archetype"]][1].append(r["decision_code"] == r["decision_gold"])
    fig, ax = plt.subplots(figsize=(3.4, 1.9))
    x = np.arange(len(arch))
    ax.bar(x - 0.2, [100 * np.mean(acc[a][0]) for a in arch], 0.4, color="#999999", label="model decides")
    ax.bar(x + 0.2, [100 * np.mean(acc[a][1]) for a in arch], 0.4, color="#2e86c1", label="code decides from extracted fields")
    ax.set_xticks(x, [a.replace("_", " ") for a in arch], rotation=30, ha="right")
    ax.set_ylabel("correct next step (%)")
    ax.set_ylim(0, 105)
    ax.legend(frameon=False, fontsize=7, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2)
    fig.savefig(OUT / "fig_decision.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = load()
    fig_language(s)
    fig_guard(s)
    fig_decision(s)
    print("figures in", OUT)


if __name__ == "__main__":
    main()
