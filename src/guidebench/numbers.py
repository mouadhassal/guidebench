"""Language-independent number extraction.

Numbers are the one kind of claim that reads the same in every language, so
they let us score answers and detect invented figures without an LLM judge.
"""
from __future__ import annotations

import itertools
import re

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SPACES = re.compile(r"[    ]")
# Tokens where digits are part of a name: eu-central-1, europe-west4, S/4HANA, 2FA, B2B, 24/7.
_NAMEISH = re.compile(r"[A-Za-zЀ-ӿ]+[-/]?\d+[A-Za-z]*|\d+[A-Za-z]{2,}\w*|\d+/\d+")
_TIME = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")
_NUM = re.compile(
    r"(?<![\w.,])("
    r"\d{1,3}(?:(?:[ ,.]\d{3})+)(?:[.,]\d{1,2})?(?!\d)"   # grouped thousands, optional decimals
    r"|\d+(?:[.,]\d+)?"                                 # plain or decimal
    r")"
)
_LIST_MARK = re.compile(r"(?m)^\s*\d{1,2}[.)]\s")


def _parse(tok: str) -> float | None:
    if re.fullmatch(r"\d+", tok):
        return float(tok)
    m = re.fullmatch(r"(\d{1,3})((?:[ ,.]\d{3})+)([.,]\d{1,2})?", tok)
    if m and not (m.group(1) == "0" and m.group(3) is None):
        seps = set(re.findall(r"[ ,.]", m.group(2)))
        dec = m.group(3)
        if len(seps) == 1 and (dec is None or dec[0] not in seps):
            whole = int(m.group(1) + re.sub(r"[ ,.]", "", m.group(2)))
            return whole + (float("0." + dec[1:]) if dec else 0.0)
    m = re.fullmatch(r"(\d+)[.,](\d+)", tok)
    if m:
        return float(f"{m.group(1)}.{m.group(2)}")
    return None


def extract(text: str) -> list[float]:
    """All numeric values in `text`, in order. Times count as their hour."""
    t = _SPACES.sub(" ", text.translate(_DIGITS))
    t = t.replace("٫", ".").replace("٬", ",")
    t = _LIST_MARK.sub(" ", t)
    t = _NAMEISH.sub(" ", t)
    out: list[float] = []
    for m in _TIME.finditer(t):
        out.append(float(int(m.group(1))))
    t = _TIME.sub(" ", t)
    for m in _NUM.finditer(t):
        v = _parse(m.group(1))
        if v is not None:
            out.append(v)
    return out


def same(a: float, b: float) -> bool:
    return abs(a - b) <= 1e-6 * max(1.0, abs(a), abs(b))


def contains(values: list[float], x: float) -> bool:
    return any(same(v, x) for v in values)


_NUMSRC = r"\d{1,3}(?:[ ,.]\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d+)?"
_MONEY = re.compile(rf"[€$£]\s?({_NUMSRC})|({_NUMSRC})\s?(?:[€$£]|eur\b|euro)", re.IGNORECASE)
_PCT = re.compile(rf"({_NUMSRC})\s?[%٪]")


def _tagged(pattern: re.Pattern, text: str) -> list[float]:
    t = _SPACES.sub(" ", text.translate(_DIGITS)).replace("٫", ".").replace("٬", ",")
    out = []
    for m in pattern.finditer(t):
        tok = next(g for g in m.groups() if g)
        v = _parse(tok)
        if v is not None:
            out.append(v)
    return out


def money(text: str) -> list[float]:
    return _tagged(_MONEY, text)


def percents(text: str) -> list[float]:
    return _tagged(_PCT, text)


def buyer_facts(text: str) -> set[float]:
    """Numbers a visitor states about themselves. Percentages and prices the visitor
    proposes (\"confirm a 50% discount\") are not facts and stay unsupported."""
    claims = set(percents(text)) | set(money(text))
    return {v for v in extract(text) if not any(same(v, c) for c in claims)}


def derived(kb_text: str, facts: set[float]) -> set[float]:
    """Figures an agent may legitimately compute from the sources: a price times
    the visitor's volume, a monthly price times 10 or 12, and a price after a
    discount that the sources state."""
    prices = set(money(kb_text))
    pcts = [p for p in percents(kb_text) if 0 < p < 100]
    out = set()
    for a in prices:
        for b in facts | {1.0}:
            for m in (1.0, 10.0, 12.0):
                out.add(round(a * b * m, 6))
                for p in pcts:
                    out.add(round(a * b * m * (1 - p / 100), 6))
    return out


def unsupported(reply: str, supported: set[float], allowed: set[float] = frozenset()) -> list[float]:
    """Numbers in `reply` that appear neither in the sources nor as an allowed derivation."""
    bad = []
    for v in extract(reply):
        if any(same(v, s) for s in supported) or round(v, 6) in allowed:
            continue
        bad.append(v)
    return bad
