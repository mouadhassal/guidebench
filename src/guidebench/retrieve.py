"""Three retrievers over the same chunks: lexical (BM25), dense (bge-m3), and an oracle."""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from . import llm
from .kb import KB, Chunk
from .numbers import contains, extract

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


def tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


class BM25:
    def __init__(self, kb: KB, k1: float = 1.2, b: float = 0.75):
        self.chunks = kb.chunks
        self.docs = [tokens(c.title + " " + c.text) for c in kb.chunks]
        self.avg = sum(map(len, self.docs)) / len(self.docs)
        df = Counter(t for d in self.docs for t in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.tf = [Counter(d) for d in self.docs]
        self.k1, self.b = k1, b

    def scores(self, query: str) -> np.ndarray:
        q = tokens(query)
        out = np.zeros(len(self.docs))
        for i, (tf, d) in enumerate(zip(self.tf, self.docs)):
            norm = self.k1 * (1 - self.b + self.b * len(d) / self.avg)
            for t in q:
                f = tf.get(t, 0)
                if f:
                    out[i] += self.idf[t] * f * (self.k1 + 1) / (f + norm)
        return out

    def search(self, query: str, k: int) -> list[Chunk]:
        s = self.scores(query)
        order = sorted(range(len(s)), key=lambda i: (-s[i], i))
        return [self.chunks[i] for i in order[:k]]


class Dense:
    MODEL = "bge-m3"

    def __init__(self, kb: KB):
        self.chunks = kb.chunks
        m = np.array(llm.embed(self.MODEL, [c.title + ". " + c.text for c in kb.chunks]))
        self.m = m / np.linalg.norm(m, axis=1, keepdims=True)

    def search(self, query: str, k: int) -> list[Chunk]:
        q = np.array(llm.embed(self.MODEL, [query])[0])
        s = self.m @ (q / np.linalg.norm(q))
        order = sorted(range(len(s)), key=lambda i: (-s[i], i))
        return [self.chunks[i] for i in order[:k]]


class Oracle:
    """Upper bound: chunks that contain the gold answer, then BM25 on the English
    wording of the question. It isolates generation errors from retrieval errors."""

    def __init__(self, kb: KB):
        self.chunks = kb.chunks
        self.bm25 = BM25(kb)

    def search(self, query_en: str, k: int, gold: list[str]) -> list[Chunk]:
        s = self.bm25.scores(query_en)
        rank = {c.id: -s[i] for i, c in enumerate(self.chunks)}
        hits: list[Chunk] = []
        for g in gold:
            cands = []
            for c in self.chunks:
                try:
                    ok = contains(extract(c.text), float(g))
                except ValueError:
                    ok = g.lower() in c.text.lower()
                if ok:
                    cands.append(c)
            # A number like "7" occurs in several chunks; keep the 2 most on-topic.
            for c in sorted(cands, key=lambda c: rank[c.id])[:2]:
                if c not in hits:
                    hits.append(c)
        for c in self.bm25.search(query_en, k):
            if len(hits) >= k:
                break
            if c not in hits:
                hits.append(c)
        return hits[:k]
