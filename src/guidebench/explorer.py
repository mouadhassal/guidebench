"""Build docs/index.html: a self-contained transcript explorer for every test conversation.

    python -m guidebench.explorer
"""
from __future__ import annotations

import json

from .kb import ROOT

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>guidebench transcripts</title>
<style>
:root{--bg:#fbfbf9;--fg:#1d1d1b;--mut:#6b6b66;--line:#e3e2dc;--card:#fff;--vis:#eef3f8;--ok:#1e8449;--bad:#b03a2e;--warn:#9a6700;--acc:#2e86c1}
@media (prefers-color-scheme:dark){:root{--bg:#161615;--fg:#ecebe6;--mut:#a3a29b;--line:#34332f;--card:#1f1f1d;--vis:#1d2833;--ok:#58d68d;--bad:#f1948a;--warn:#f4d03f;--acc:#5dade2}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 16px 8px;max-width:1180px;margin:auto}h1{font-size:20px;margin:0 0 4px}header p{margin:0;color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;padding:8px 16px;max-width:1180px;margin:auto;position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:2}
select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--fg);max-width:100%}
main{max-width:1180px;margin:auto;padding:12px 16px 60px;display:grid;gap:16px}
.cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px}
.conv{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.conv h2{font-size:14px;margin:0 0 8px;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.turn{margin:10px 0;border-top:1px dashed var(--line);padding-top:8px}
.v{background:var(--vis);border-radius:8px;padding:6px 9px;font-size:14px}
.a{padding:6px 2px 2px;font-size:14px;white-space:pre-wrap;overflow-wrap:anywhere}
.tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:4px}
.t{font-size:11.5px;border:1px solid var(--line);border-radius:999px;padding:1px 8px;color:var(--mut)}
.t.ok{color:var(--ok);border-color:var(--ok)}.t.bad{color:var(--bad);border-color:var(--bad)}.t.warn{color:var(--warn);border-color:var(--warn)}
mark{background:transparent;color:var(--bad);font-weight:700;text-decoration:underline wavy}
details{font-size:12px;color:var(--mut)}.dec{font-size:13px;margin-top:8px}
[dir=rtl]{text-align:right}
</style></head><body>
<header><h1>guidebench: transcript explorer</h1>
<p>Every test conversation, unedited. Red wavy figures are numbers the website does not support. Tags show the deterministic scores. Source: <a href="https://github.com/mouadhassal/guidebench">github.com/mouadhassal/guidebench</a></p></header>
<div class="bar">
<select id="cond"></select><select id="persona"></select><select id="lang"></select><select id="cmp"></select>
</div>
<main id="main"></main>
<script>
const D = __DATA__;
const LN = {en:"English",et:"Estonian",lt:"Lithuanian",ru:"Russian",fr:"French",de:"German",ar:"Arabic"};
const $ = id => document.getElementById(id);
function fill(sel, items, label){ sel.innerHTML = items.map(([v,t]) => `<option value="${v}">${t}</option>`).join(""); }
fill($("cond"), Object.keys(D.conds).map(c => [c, D.names[c] || c]));
fill($("persona"), D.personas.map(p => [p.id, `${p.id} · ${p.archetype.replace("_"," ")}`]));
fill($("lang"), Object.keys(LN).map(l => [l, LN[l]]));
fill($("cmp"), [["", "compare with: none"], ...Object.keys(LN).map(l => [l, "compare with: " + LN[l]])]);
$("lang").value = "et"; $("cmp").value = "en";
function esc(s){ return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c])); }
function markNums(text, bad){
  let h = esc(text);
  if (!bad.length) return h;
  return h.replace(/\d[\d\s.,٫٬]*\d|\d/g, m => {
    const v = parseFloat(m.replace(/[\s٬]/g,"").replace(/,(\d{3})(?!\d)/g,"$1").replace(",",".").replace("٫","."));
    return bad.some(b => Math.abs(b - v) < 1e-6 * Math.max(1, Math.abs(b))) ? `<mark>${m}</mark>` : m;
  });
}
function conv(cond, pid, lang){
  const r = (D.conds[cond] || {})[pid + "|" + lang];
  if (!r) return `<div class="conv">No conversation.</div>`;
  const rtl = lang === "ar" ? ' dir="rtl"' : "";
  let h = `<div class="conv"><h2><span>${LN[lang]}</span><span class="t">${(D.names[cond]||cond)}</span></h2>`;
  r.turns.forEach((t, i) => {
    const tags = [];
    t.asks.forEach(a => tags.push(`<span class="t ${a.ok ? "ok" : "bad"}">${a.unknown ? "should abstain" : a.id}: ${a.ok ? "correct" : "wrong"}${a.gold ? " · gold " + a.gold : ""}</span>`));
    if (t.unsupported.length) tags.push(`<span class="t bad">unsupported: ${t.unsupported.join(", ")}</span>`);
    if (!t.lang_ok) tags.push(`<span class="t warn">wrong language</span>`);
    if (t.probe === "injection") tags.push(`<span class="t ${t.accepts_discount ? "bad" : "ok"}">${t.accepts_discount ? "accepted fake discount" : "refused fake discount"}</span>`);
    if (t.probe === "leak") tags.push(`<span class="t ${t.canary ? "bad" : "ok"}">${t.canary ? "leaked secret code" : "no secret leaked"}</span>`);
    if (t.probe === "emails") tags.push(`<span class="t ${t.email_leak ? "bad" : "ok"}">${t.email_leak ? "invented emails" : "no emails"}</span>`);
    if (t.guarded) tags.push(`<span class="t warn">guard rewrote the draft</span>`);
    tags.push(`<span class="t">${t.seconds.toFixed(1)} s</span>`);
    h += `<div class="turn"><div class="v"${rtl}>${esc(t.text)}</div><div class="a"${rtl}>${markNums(t.reply, t.unsupported)}</div>
      <div class="tags">${tags.join("")}</div>
      ${t.draft ? `<details><summary>draft before guard</summary><div${rtl}>${esc(t.draft)}</div></details>` : ""}
      <details><summary>retrieved sections</summary>${t.retrieved.join(" · ")}</details></div>`;
  });
  const ok = x => x === r.gold ? "ok" : "bad";
  h += `<div class="dec">Next step: gold <b>${r.gold}</b> · model <span class="t ${ok(r.llm)}">${r.llm}</span> · code from extracted fields <span class="t ${ok(r.code)}">${r.code}</span></div></div>`;
  return h;
}
function render(){
  const c = $("cond").value, p = $("persona").value, l = $("lang").value, k = $("cmp").value;
  $("main").innerHTML = `<div class="cols">${conv(c,p,l)}${k && k !== l ? conv(c,p,k) : ""}</div>`;
  try { localStorage.setItem("gb", JSON.stringify([c,p,l,k])); } catch(e) {}
}
try { const s = JSON.parse(localStorage.getItem("gb")); if (s) { ["cond","persona","lang","cmp"].forEach((id,i) => { if (s[i] !== undefined && [...$(id).options].some(o => o.value === s[i])) $(id).value = s[i]; }); } } catch(e) {}
["cond","persona","lang","cmp"].forEach(id => $(id).addEventListener("change", render));
render();
</script></body></html>"""

NAMES = {"qwen3-8b_bm25": "qwen3:8b · BM25", "qwen3-8b_dense": "qwen3:8b · bge-m3",
         "qwen3-8b_oracle": "qwen3:8b · oracle retrieval", "qwen3-8b_dense_guard": "qwen3:8b · bge-m3 + guard",
         "gemma3-4b_dense": "gemma3:4b · bge-m3", "gemma3-4b_dense_guard": "gemma3:4b · bge-m3 + guard"}


def main():
    runs, scored_dir = ROOT / "results" / "runs", ROOT / "results" / "scored"
    data = {"names": NAMES, "conds": {}, "personas": []}
    seen = set()
    for f in sorted(runs.glob("*.jsonl")):
        rows = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()]
        scored = [json.loads(l) for l in (scored_dir / f.name).read_text(encoding="utf-8").splitlines()]
        out = {}
        for r, s in zip(rows, scored):
            if r["persona"] not in seen:
                seen.add(r["persona"])
                data["personas"].append({"id": r["persona"], "archetype": r["archetype"]})
            turns = []
            for t, ts in zip(r["turns"], s["turns"]):
                golds = {a["id"]: ", ".join(a["gold"].get("any", []) + a["gold"].get("all", [])) for a in t["asks"]}
                turns.append({"text": t["text"], "reply": t["reply"], "retrieved": t["retrieved"],
                              "draft": t.get("draft"), "guarded": t.get("guarded", False), "seconds": t["seconds"],
                              "asks": [{**a, "gold": golds.get(a["id"], "")} for a in ts["asks"]],
                              **{k: ts.get(k) for k in ("unsupported", "lang_ok", "probe", "accepts_discount",
                                                        "canary", "email_leak")}})
            out[f"{r['persona']}|{r['lang']}"] = {"turns": turns, "gold": s["decision_gold"],
                                                  "llm": s["decision_llm"], "code": s["decision_code"]}
        data["conds"][f.stem] = out
    data["personas"].sort(key=lambda p: p["id"])
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    html = PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    (docs / "index.html").write_text(html, encoding="utf-8")
    print(f"docs/index.html: {len(html) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
