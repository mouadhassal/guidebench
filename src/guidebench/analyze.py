"""Score every run, compute the pre-registered metrics with persona-clustered
bootstrap intervals, and write results/summary.json, results/verdicts.json and results/tables.md.

    python -m guidebench.analyze [--runs results/runs]
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from .kb import ROOT
from .score import score_conversation

SEED = 20261011
B = 10_000
NON_EN = ["et", "lt", "ru", "fr", "de", "ar"]
LANGS = ["en"] + NON_EN
GOOD = {"book_demo", "human_handoff"}


def load_scored(runs: Path, judge: bool = True) -> dict[str, list[dict]]:
    out = {}
    cache_dir = runs.parent / "scored"
    cache_dir.mkdir(exist_ok=True)
    for f in sorted(runs.glob("*.jsonl")):
        cache = cache_dir / f.name
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
        if cache.exists() and cache.stat().st_mtime >= f.stat().st_mtime:
            scored = [json.loads(l) for l in cache.read_text(encoding="utf-8").splitlines()]
        else:
            scored = [score_conversation(r, judge) for r in rows]
            cache.write_text("\n".join(json.dumps(s, ensure_ascii=False) for s in scored), encoding="utf-8")
        out[f.stem] = scored
    return out


# ---- unit-level records: each metric is a mean over units clustered by persona ----

def units(rows: list[dict], metric: str) -> list[tuple[str, str, float]]:
    """(persona, lang, value) triples for a metric."""
    u = []
    for r in rows:
        p, l = r["persona"], r["lang"]
        if metric == "answer":
            u += [(p, l, float(a["ok"])) for t in r["turns"] for a in t["asks"] if not a["unknown"]]
        elif metric == "abstain":
            u += [(p, l, float(a["ok"])) for t in r["turns"] for a in t["asks"] if a["unknown"]]
        elif metric == "invented":
            u += [(p, l, float(bool(t["unsupported"]))) for t in r["turns"]]
        elif metric == "lang_ok":
            u += [(p, l, float(t["lang_ok"])) for t in r["turns"]]
        elif metric == "decision_llm":
            u.append((p, l, float(r["decision_llm"] == r["decision_gold"])))
        elif metric == "decision_code":
            u.append((p, l, float(r["decision_code"] == r["decision_gold"])))
        elif metric == "size_ok":
            if r["size_ok"] is not None:
                u.append((p, l, float(r["size_ok"])))
        elif metric == "accepts_discount":
            u += [(p, l, float(t["accepts_discount"])) for t in r["turns"] if "accepts_discount" in t]
        elif metric == "canary":
            u += [(p, l, float(t["canary"])) for t in r["turns"] if t["probe"] == "leak"]
        elif metric == "email_leak":
            u += [(p, l, float(t["email_leak"])) for t in r["turns"] if t["probe"] == "emails"]
        elif metric == "badfit_to_sales":   # bad-fit visitors routed to a human seller
            if r["decision_gold"] not in GOOD:
                u.append((p, l, float(r["decision_llm"] in GOOD)))
        elif metric == "goodfit_lost":      # good-fit visitors not routed to a human seller
            if r["decision_gold"] in GOOD:
                u.append((p, l, float(r["decision_llm"] not in GOOD)))
        elif metric == "seconds":
            u += [(p, l, t["seconds"]) for t in r["turns"]]
        else:
            raise KeyError(metric)
    return u


def mean(u, langs=None) -> float:
    v = [x for _, l, x in u if langs is None or l in langs]
    return float(np.mean(v)) if v else float("nan")


def boot(stat, personas: list[str], rng) -> np.ndarray:
    idx = rng.integers(0, len(personas), size=(B, len(personas)))
    return np.array([stat([personas[i] for i in row]) for row in idx])


def _agg(u, sample, langs=None):
    by = defaultdict(list)
    for p, l, x in u:
        if langs is None or l in langs:
            by[p].append(x)
    vals = [x for p in sample for x in by.get(p, [])]
    return float(np.mean(vals)) if vals else float("nan")


def ci(stat, personas, seed=SEED):
    rng = np.random.default_rng(seed)
    b = boot(stat, personas, rng)
    b = b[~np.isnan(b)]
    return [float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))]


def gap(u, personas):
    """English minus mean of non-English languages (positive = English better)."""
    f = lambda s: _agg(u, s, ["en"]) - _agg(u, s, NON_EN)
    return f(personas), ci(f, personas)


def diff(u1, u0, personas):
    """Condition 1 minus condition 0, same units."""
    f = lambda s: _agg(u1, s) - _agg(u0, s)
    return f(personas), ci(f, personas)


METRICS = ["answer", "abstain", "invented", "lang_ok", "decision_llm", "decision_code", "size_ok",
           "accepts_discount", "canary", "email_leak", "badfit_to_sales", "goodfit_lost", "seconds"]


def summarize(scored: dict[str, list[dict]]) -> dict:
    s = {}
    for cond, rows in scored.items():
        s[cond] = {m: {"all": mean(units(rows, m)), **{l: mean(units(rows, m), [l]) for l in LANGS}}
                   for m in METRICS}
        s[cond]["n_conversations"] = len(rows)
    return s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="results/runs")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args(argv)
    runs = ROOT / a.runs
    scored = load_scored(runs, not a.no_judge)
    summary = summarize(scored)
    out = runs.parent
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    from .verdicts import verdicts, tables
    v = verdicts(scored)
    (out / "verdicts.json").write_text(json.dumps(v, indent=1), encoding="utf-8")
    (out / "tables.md").write_text(tables(summary, v), encoding="utf-8")
    print((out / "tables.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
