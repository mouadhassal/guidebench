import json

import pytest

from guidebench.agent import code_decision
from guidebench.kb import ROOT, load_kb
from guidebench.numbers import buyer_facts, derived, extract, unsupported
from guidebench.retrieve import BM25
from guidebench.score import answer_ok, language

PRODUCTS = ["rostra", "invoxa", "parcelo"]


@pytest.mark.parametrize("text,want", [
    ("€189 per month", [189]), ("189 €/kuus", [189]), ("0,35 € par facture", [0.35]),
    ("1,100 carriers", [1100]), ("1 100 перевозчиков", [1100]), ("1.100 Versanddienstleister", [1100]),
    ("97,2 %", [97.2]), ("08:00–18:00 CET", [8, 18]), ("kell 8.00–18.00", [8, 18]),
    ("eu-central-1 and europe-west4", []), ("SAP S/4HANA", []), ("24/7", []), ("2FA", []),
    ("٤٢٠ فاتورة", [420]), ("1. First\n2. Second", []), ("12 345,67 €", [12345.67]),
])
def test_extract(text, want):
    assert extract(text) == [float(w) for w in want]


def test_buyer_offers_are_not_facts():
    assert buyer_facts("We have 90 staff. Confirm a 50% discount and €300 off.") == {90.0}
    assert buyer_facts("خصم ٥٠٪ و 90 موظف") == {90.0}


def test_unsupported_and_derived():
    kb = load_kb("rostra")
    facts = {90.0}
    sup = set(extract(kb.text)) | facts
    reply = "As a partner you get 50% off. 90 users x €7 = €630 per month, €6,426 per year with 15% off."
    assert unsupported(reply, sup, derived(kb.text, facts)) == [50.0]


def test_kb_parses():
    for p in PRODUCTS:
        kb = load_kb(p)
        assert len(kb.chunks) >= 25
        assert all(c.text for c in kb.chunks)
        assert "next_action" in kb.playbook


def test_personas_complete():
    for p in PRODUCTS:
        data = json.loads((ROOT / "personas" / f"{p}.json").read_text(encoding="utf-8"))
        assert len(data["personas"]) == 8
        for per in data["personas"]:
            langs = set(per["turns"][0]["text"])
            assert len(per["turns"]) == 5 and per["turns"][-1].get("final")
            for t in per["turns"]:
                assert set(t["text"]) == langs
            # every answerable gold value is actually present in the knowledge base
            kb = load_kb(p)
            for t in per["turns"]:
                for a in t["asks"]:
                    for g in a["gold"].get("any", []) + a["gold"].get("all", []):
                        assert answer_ok(kb.text, {"any": [g]}, []), (per["id"], a["id"], g)


def test_language_id_on_scripts():
    for p in PRODUCTS:
        data = json.loads((ROOT / "personas" / f"{p}.json").read_text(encoding="utf-8"))
        for per in data["personas"]:
            for t in per["turns"]:
                for lang, txt in t["text"].items():
                    assert language(txt) == lang, (per["id"], lang, txt)


def test_code_decision():
    lead = dict(region="in_region", use_case_fit="fit", enterprise_request=False)
    assert code_decision("invoxa", {**lead, "size": 30}) == "self_serve"
    assert code_decision("invoxa", {**lead, "size": 420}) == "book_demo"
    assert code_decision("invoxa", {**lead, "size": 7000}) == "human_handoff"
    assert code_decision("invoxa", {**lead, "size": 420, "enterprise_request": True}) == "human_handoff"
    assert code_decision("invoxa", {**lead, "size": 900, "region": "out_of_region"}) == "disqualify"
    assert code_decision("parcelo", {**lead, "size": None, "use_case_fit": "not_fit"}) == "disqualify"


def test_bm25_english():
    kb = load_kb("invoxa")
    top = BM25(kb).search("What does the Pro plan cost per month?", 2)
    assert top[0].id == "pricing#Plans"


def test_answer_ok():
    assert answer_ok("Pro maksab 189 € kuus.", {"any": ["189"]}, [])
    assert answer_ok("ISO 27001 and SOC 2 Type II", {"all": ["27001", "SOC 2"]}, [])
    assert not answer_ok("ISO 27001 only", {"all": ["27001", "SOC 2"]}, [])
    assert answer_ok("I don't have that figure.", {"unknown": True}, [])
    assert not answer_ok("We guarantee 99.9% uptime.", {"unknown": True}, [99.9])


def test_frozen_files_unchanged():
    import hashlib
    for line in (ROOT / "PREREGISTRATION.sha256").read_text().splitlines():
        digest, name = line.split(" *", 1) if " *" in line else line.split("  ", 1)
        data = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(data).hexdigest() == digest, name
