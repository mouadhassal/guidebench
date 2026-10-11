# Deviations and additions after the freeze

**Pre-registered procedure.** No change. All six conditions ran on the frozen code, prompts, knowledge bases and buyer scripts (`PREREGISTRATION.sha256` still matches; CI checks it).

**Audit 1 sample size.** The plan said 60 randomly chosen flagged replies. C2 had only 24 flagged replies, so all 24 were audited.

**Additions, clearly separated from the pre-registered results:**
1. **Exploratory routing metrics for code decisions** (bad-fit sent to sales, good-fit lost, both computed on `decision_code`). The pre-registration defined these for the model's own decision only.
2. **Exploratory unit-aware guard** (`src/guidebench/unitguard.py`, `results/exploratory/`). It was added after H6 failed because "50" appears on both sites as a count. A first launch was interrupted and relaunched, so duplicate rows appeared; the file keeps the last complete row per conversation, and all model calls are cached and deterministic.
3. **Hand corrections of the judge** are reported next to the pre-registered judge numbers (`audit/AUDIT_JUDGE.md`). The verdicts use the pre-registered judge numbers.
4. **The prompt-leak finding** (one paraphrase of the system prompt) comes from reading the extraction replies. The pre-registered H7 measure (canary string) was 0, and H7 is reported as held, with this caveat.

**Code after the freeze** (not used by any pre-registered number): `explorer.py` (transcript page), `figures.py` labels, `check.py` (CI), `unitguard.py`.
