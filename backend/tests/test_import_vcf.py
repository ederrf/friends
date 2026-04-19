"""Testes da importacao VCF (13.11).

Cobertura:
- parser puro (`parse_vcf`, line-folding, escapes, N-field fallback)
- parametros de propriedade (TEL;TYPE=CELL:...)
- quoted-printable
- CATEGORIES -> tags
- preview/commit via HTTP
- erros: arquivo vazio
"""

from __future__ import annotations

import json

import pytest

from app.services import import_service
from app.services.import_service import (
    _name_from_n,
    _unfold_vcf,
    parse_vcf,
)


VCARD_SIMPLE = """BEGIN:VCARD
VERSION:3.0
FN:Ana Silva
TEL;TYPE=CELL:+5511999990000
EMAIL;TYPE=HOME:ana@example.com
BDAY:19900315
NOTE:Amiga de longa data
CATEGORIES:rpg,cerveja
END:VCARD
"""


# ── Helpers ──────────────────────────────────────────────────────


def test_unfold_vcf_joins_continuation_lines():
    text = "NOTE:primeira parte\n segunda parte\n terceira\n"
    out = _unfold_vcf(text)
    # linhas continuacao somam a primeira sem repetir o espaco inicial
    assert out == ["NOTE:primeira partesegunda parteterceira", ""]


def test_name_from_n_uses_given_then_family():
    assert _name_from_n("Silva;Ana;;;") == "Ana Silva"
    assert _name_from_n("Silva;Ana;Maria;;") == "Ana Maria Silva"
    assert _name_from_n(";Ana;;;") == "Ana"
    assert _name_from_n("Silva;;;;") == "Silva"


# ── Parser basico ────────────────────────────────────────────────


def test_parse_vcf_single_card_populates_all_fields():
    candidates = parse_vcf(VCARD_SIMPLE)
    assert len(candidates) == 1
    c = candidates[0]
    assert c.source_index == 0
    assert c.name == "Ana Silva"
    assert c.phone == "+5511999990000"
    assert c.email == "ana@example.com"
    assert c.birthday is not None and c.birthday.isoformat() == "1990-03-15"
    assert c.notes == "Amiga de longa data"
    assert c.tags == ["rpg", "cerveja"]


def test_parse_vcf_multiple_cards_preserve_source_index():
    text = VCARD_SIMPLE + (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Bruno\nTEL:22222\nEND:VCARD\n"
    )
    candidates = parse_vcf(text)
    assert [c.source_index for c in candidates] == [0, 1]
    assert candidates[1].name == "Bruno"
    assert candidates[1].phone == "22222"


def test_parse_vcf_falls_back_to_n_when_fn_missing():
    text = "BEGIN:VCARD\nVERSION:3.0\nN:Silva;Ana;;;\nTEL:11111\nEND:VCARD\n"
    candidates = parse_vcf(text)
    assert len(candidates) == 1
    assert candidates[0].name == "Ana Silva"


def test_parse_vcf_skips_cards_without_any_name():
    text = "BEGIN:VCARD\nVERSION:3.0\nTEL:11111\nEND:VCARD\n" + VCARD_SIMPLE
    candidates = parse_vcf(text)
    # primeiro card sem nome eh descartado, source_index do segundo eh 1
    assert len(candidates) == 1
    assert candidates[0].source_index == 1
    assert candidates[0].name == "Ana Silva"


def test_parse_vcf_empty_returns_empty():
    assert parse_vcf("") == []
    assert parse_vcf("   \n\n") == []


def test_parse_vcf_first_value_wins_for_duplicate_fields():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\n"
        "TEL;TYPE=CELL:11111\nTEL;TYPE=HOME:22222\n"
        "EMAIL:a@x.com\nEMAIL:b@x.com\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.phone == "11111"
    assert c.email == "a@x.com"


def test_parse_vcf_categories_deduplicates_and_lowercases():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\n"
        "CATEGORIES:RPG,Cerveja;rpg\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.tags == ["rpg", "cerveja"]


def test_parse_vcf_handles_escapes_in_note():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\n"
        "NOTE:linha 1\\nlinha 2 com \\, virgula\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.notes == "linha 1\nlinha 2 com , virgula"


def test_parse_vcf_handles_line_folding_in_note():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\n"
        "NOTE:primeira parte\n  segunda parte\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    # primeiro espaco e removido pelo unfold; segundo espaco fica
    assert c.notes == "primeira parte segunda parte"


def test_parse_vcf_quoted_printable_decodes_utf8():
    # "Jo=C3=A3o" eh "João" em UTF-8 quoted-printable
    text = (
        "BEGIN:VCARD\nVERSION:2.1\n"
        "FN;CHARSET=UTF-8;ENCODING=QUOTED-PRINTABLE:Jo=C3=A3o\n"
        "END:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.name == "João"


def test_parse_vcf_birthday_iso_with_dashes():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\nBDAY:1990-03-15\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.birthday is not None and c.birthday.isoformat() == "1990-03-15"


def test_parse_vcf_birthday_partial_yyyymmdd_absent_returns_none():
    text = (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Ana\nBDAY:--03-15\nEND:VCARD\n"
    )
    c = parse_vcf(text)[0]
    assert c.birthday is None


def test_parse_vcf_crlf_line_endings():
    text = VCARD_SIMPLE.replace("\n", "\r\n")
    candidates = parse_vcf(text)
    assert len(candidates) == 1
    assert candidates[0].name == "Ana Silva"


def test_preview_vcf_returns_empty_mapping_and_fields():
    preview = import_service.preview_vcf(VCARD_SIMPLE)
    assert preview.total == 1
    assert preview.detected_fields == []
    assert preview.suggested_mapping == {}


# ── Integracao HTTP ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_vcf_preview_endpoint(client):
    response = await client.post(
        "/api/import/vcf/preview",
        files={"file": ("contatos.vcf", VCARD_SIMPLE.encode("utf-8"), "text/vcard")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["detected_fields"] == []
    assert body["suggested_mapping"] == {}
    cand = body["candidates"][0]
    assert cand["name"] == "Ana Silva"
    assert cand["phone"] == "+5511999990000"
    assert cand["tags"] == ["rpg", "cerveja"]


@pytest.mark.asyncio
async def test_vcf_commit_persists_approved(client):
    text = VCARD_SIMPLE + (
        "BEGIN:VCARD\nVERSION:3.0\nFN:Bruno Alves\nTEL:22222\nEND:VCARD\n"
    )
    payload = json.dumps(
        {
            "approved_indexes": [1],
            "default_category": "upgrade",
            "default_cadence": "weekly",
        }
    )
    response = await client.post(
        "/api/import/vcf/commit",
        files={"file": ("c.vcf", text.encode("utf-8"), "text/vcard")},
        data={"payload": payload},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 0

    listed = (await client.get("/api/friends")).json()
    assert [f["name"] for f in listed] == ["Bruno Alves"]
    bruno = listed[0]
    assert bruno["cadence"] == "weekly"
    assert bruno["category"] == "upgrade"


@pytest.mark.asyncio
async def test_vcf_commit_empty_returns_error(client):
    payload = json.dumps(
        {
            "approved_indexes": [],
            "default_category": "upgrade",
            "default_cadence": "weekly",
        }
    )
    response = await client.post(
        "/api/import/vcf/commit",
        files={"file": ("c.vcf", b"", "text/vcard")},
        data={"payload": payload},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_EMPTY_FILE"


@pytest.mark.asyncio
async def test_vcf_commit_skipped_unknown_index(client):
    payload = json.dumps(
        {
            "approved_indexes": [0, 42],
            "default_category": "rekindle",
            "default_cadence": "monthly",
        }
    )
    response = await client.post(
        "/api/import/vcf/commit",
        files={"file": ("c.vcf", VCARD_SIMPLE.encode("utf-8"), "text/vcard")},
        data={"payload": payload},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert any("42" in e for e in body["errors"])


@pytest.mark.asyncio
async def test_vcf_commit_bad_payload_returns_400(client):
    response = await client.post(
        "/api/import/vcf/commit",
        files={"file": ("c.vcf", VCARD_SIMPLE.encode("utf-8"), "text/vcard")},
        data={"payload": "{not json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_BAD_PAYLOAD"
