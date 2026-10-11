"""Exploratory (not pre-registered): a unit-aware version of the guard.

The pre-registered guard compares bare numbers, so "50%" passes whenever the website
mentions 50 of anything (Invoxa: "up to 50 invoices"; Parcelo: "up to 50 shipments").
That is exactly what happened to the fake-discount injection. This variant checks
percentages only against the website's percentages, and euro amounts only against its
prices and their derivations.
"""
from __future__ import annotations

from . import llm
from .agent import GUARD, SCHEMA, Agent, Config, _parse
from .numbers import buyer_facts, derived, extract, money, percents, same, unsupported


def unsupported_units(reply: str, kb_text: str, facts: set[float]) -> list[float]:
    kb_pct, kb_money = set(percents(kb_text)), set(money(kb_text))
    allowed = derived(kb_text, facts)
    bad = [p for p in percents(reply) if not any(same(p, k) for k in kb_pct)]
    bad += [m for m in money(reply)
            if not any(same(m, k) for k in kb_money) and round(m, 6) not in allowed]
    tagged = set(percents(reply)) | set(money(reply))
    plain = unsupported(reply, set(extract(kb_text)) | facts, allowed)
    bad += [v for v in plain if not any(same(v, t) for t in tagged)]
    return bad


class UnitGuardAgent(Agent):
    """Same agent and prompt; only the guard's check is unit-aware."""

    def run(self, turns, lang):
        history, facts, log = [], set(), []
        prev, prev_en = "", ""
        for t in turns:
            text, text_en = t["text"][lang], t["text"]["en"]
            facts |= buyer_facts(text)
            gold = [g for a in t["asks"] for g in a["gold"].get("any", []) + a["gold"].get("all", [])]
            chunks = self.retrieve(f"{prev} {text}".strip(), f"{prev_en} {text_en}".strip(), gold)
            user = f"Visitor: {text}\n\nSOURCES:\n" + "\n".join(c.render() for c in chunks)
            msgs = [{"role": "system", "content": self.system}, *history, {"role": "user", "content": user}]
            r = llm.chat(self.cfg.model, msgs, SCHEMA)
            out, ok = _parse(r["content"])
            calls, guarded, draft = [r], False, None
            bad = unsupported_units(out["reply"], self.kb.text, facts)
            if bad:
                draft = out["reply"]
                fix = msgs + [{"role": "assistant", "content": r["content"]},
                              {"role": "user", "content": GUARD.format(bad=", ".join(f"{b:g}" for b in bad))}]
                r2 = llm.chat(self.cfg.model, fix, SCHEMA)
                out2, ok2 = _parse(r2["content"])
                calls.append(r2)
                if ok2:
                    out, ok, guarded = out2, ok2, True
            log.append({
                "lang": lang, "text": text, "asks": t["asks"], "probe": t.get("probe"),
                "final": bool(t.get("final")), "retrieved": [c.id for c in chunks],
                "reply": out["reply"], "lead": out.get("lead", {}), "next_action": out["next_action"],
                "parsed": ok, "guarded": guarded, "draft": draft,
                "seconds": sum(c["seconds"] for c in calls),
                "prompt_tokens": sum(c["prompt_tokens"] for c in calls),
                "output_tokens": sum(c["output_tokens"] for c in calls),
                "buyer_numbers": sorted(facts),
            })
            history += [{"role": "user", "content": f"Visitor: {text}"},
                        {"role": "assistant", "content": out["reply"]}]
            prev, prev_en = text, text_en
        return log


def main():
    import json
    import time

    from .kb import ROOT, load_kb
    from .run import LANGS, personas
    cfg = Config("qwen3:8b", "dense", True)
    out = ROOT / "results" / "exploratory" / "qwen3-8b_dense_unitguard.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {(json.loads(l)["persona"], json.loads(l)["lang"]) for l in out.read_text(encoding="utf-8").splitlines()} if out.exists() else set()
    t0 = time.time()
    with out.open("a", encoding="utf-8") as f:
        for key in ("invoxa", "parcelo"):
            agent = UnitGuardAgent(load_kb(key), cfg)
            for p in personas(key):
                for lang in LANGS:
                    if (p["id"], lang) in done:
                        continue
                    turns = agent.run(p["turns"], lang)
                    f.write(json.dumps({"condition": "qwen3-8b_dense_unitguard", "product": key, "persona": p["id"],
                                        "archetype": p["archetype"], "gold": p["gold"], "lang": lang,
                                        "turns": turns}, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"[unitguard] {p['id']} {lang} ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
