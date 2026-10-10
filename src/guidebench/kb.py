"""Knowledge bases: a product website written as markdown pages, split into sections."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "kb"


@dataclass(frozen=True)
class Chunk:
    id: str        # "pricing#Plans"
    page: str
    title: str
    text: str

    def render(self) -> str:
        return f"[{self.id}] {self.text}"


@dataclass(frozen=True)
class KB:
    product: str     # display name, e.g. "Invoxa"
    key: str         # folder name, e.g. "invoxa"
    tagline: str
    chunks: tuple[Chunk, ...]
    playbook: str

    @property
    def text(self) -> str:
        return "\n".join(c.text for c in self.chunks)


def load_kb(key: str) -> KB:
    raw = (KB_DIR / key / "pages.md").read_text(encoding="utf-8")
    front, body = raw.split("---", 2)[1:]
    meta = dict(l.split(":", 1) for l in front.strip().splitlines())
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    chunks: list[Chunk] = []
    page = ""
    for block in re.split(r"(?m)^(?=#{1,2} )", body):
        block = block.strip()
        if not block:
            continue
        head, _, rest = block.partition("\n")
        if head.startswith("# page:"):
            page = head.split(":", 1)[1].split("|")[0].strip()
            continue
        title = head.lstrip("#").strip()
        text = " ".join(rest.split())
        chunks.append(Chunk(f"{page}#{title}", page, title, text))
    playbook = (KB_DIR / key / "playbook.md").read_text(encoding="utf-8").strip()
    return KB(meta["product"], key, meta["tagline"], tuple(chunks), playbook)
