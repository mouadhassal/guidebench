"""CI check without a GPU: every deterministic score is recomputed from the committed
transcripts and must match the committed scores; the verdicts must follow from them."""
from __future__ import annotations

import json
import sys

from .kb import ROOT
from .score import score_conversation
from .verdicts import verdicts

JUDGED = {"accepts_discount"}


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in JUDGED}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def rounded(x):
    """Bootstrap sums can differ in the last bits across platforms."""
    if isinstance(x, dict):
        return {k: rounded(v) for k, v in x.items()}
    if isinstance(x, list):
        return [rounded(v) for v in x]
    if isinstance(x, float):
        return round(x, 6)
    return x


def main() -> int:
    runs, scored_dir = ROOT / "results" / "runs", ROOT / "results" / "scored"
    scored = {}
    bad = 0
    for f in sorted(runs.glob("*.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
        committed = [json.loads(l) for l in (scored_dir / f.name).read_text(encoding="utf-8").splitlines()]
        assert len(rows) == len(committed), f.name
        for r, c in zip(rows, committed):
            if strip(score_conversation(r, judge=False)) != strip(c):
                bad += 1
                print("mismatch", f.stem, r["persona"], r["lang"])
        scored[f.stem] = committed
        print(f"{f.stem}: {len(rows)} conversations re-scored")
    v = verdicts(scored)
    committed_v = json.loads((ROOT / "results" / "verdicts.json").read_text(encoding="utf-8"))
    if rounded(json.loads(json.dumps(v))) != rounded(committed_v):
        bad += 1
        print("verdicts differ from results/verdicts.json")
    print("OK" if not bad else f"{bad} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
