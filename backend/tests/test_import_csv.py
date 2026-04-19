"""Testes da importacao CSV (13.10).

Cobertura:
- parser puro (`parse_csv`, `guess_field`, `parse_birthday`, `_split_tags`)
- preview com autodeteccao
- preview com mapping customizado
- commit (integracao via httpx)
- erros: mapping JSON invalido, mapping ausente no commit, arquivo vazio
"""

from __future__ import annotations

import json

import pytest

from app.services import import_service
from app.services.import_service import (
    _split_tags,
    build_candidates,
    guess_field,
    parse_birthday,
    parse_csv,
)


# ── Parser puro ──────────────────────────────────────────────────


def test_parse_csv_default_comma():
    text = "name,phone\nAna,11111\nBruno,22222\n"
    headers, rows = parse_csv(text)
    assert headers == ["name", "phone"]
    assert rows == [
        {"name": "Ana", "phone": "11111"},
        {"name": "Bruno", "phone": "22222"},
    ]


def test_parse_csv_semicolon_separator():
    text = "Nome;Telefone\nAna;11111\nBruno;22222\n"
    headers, rows = parse_csv(text)
    assert headers == ["Nome", "Telefone"]
    assert rows[0] == {"Nome": "Ana", "Telefone": "11111"}


def test_parse_csv_strips_bom_and_blank_lines():
    text = "\ufeffname,phone\nAna,11111\n\n\nBruno,22222\n"
    headers, rows = parse_csv(text)
    assert headers == ["name", "phone"]
    assert len(rows) == 2


def test_parse_csv_empty_returns_empty():
    assert parse_csv("") == ([], [])


def test_parse_csv_handles_quotes_with_separator_inside():
    text = 'name,notes\nAna,"linha 1, linha 2"\n'
    _, rows = parse_csv(text)
    assert rows[0]["notes"] == "linha 1, linha 2"


# ── Autodeteccao ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "header,expected",
    [
        ("Nome", "name"),
        ("Full Name", "name"),
        ("Display Name", "name"),
        ("Phone 1 - Value", "phone"),
        ("Telefone Celular", "phone"),
        ("Whatsapp", "phone"),
        ("E-mail", "email"),
        ("Email Address", "email"),
        ("Birthday", "birthday"),
        ("Aniversario", "birthday"),
        ("Notes", "notes"),
        ("Observacoes", "notes"),
        ("Tags", "tags"),
        ("Grupos", "tags"),
        ("ID", "ignore"),
        ("", "ignore"),
        ("Random Column", "ignore"),
    ],
)
def test_guess_field_heuristics(header: str, expected: str):
    assert guess_field(header) == expected


# ── parse_birthday ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected_iso",
    [
        ("1990-03-15", "1990-03-15"),
        ("15/03/1990", "1990-03-15"),
        ("15-03-1990", "1990-03-15"),
        ("19900315", "1990-03-15"),
        ("1990/03/15", "1990-03-15"),
    ],
)
def test_parse_birthday_known_formats(raw: str, expected_iso: str):
    parsed = parse_birthday(raw)
    assert parsed is not None
    assert parsed.isoformat() == expected_iso


def test_parse_birthday_invalid_returns_none():
    assert parse_birthday("nao-e-data") is None
    assert parse_birthday("") is None
    assert parse_birthday("--03-15") is None  # vCard parcial, ainda nao suportado


# ── tags split ──────────────────────────────────────────────────


def test_split_tags_dedup_and_lowercase():
    assert _split_tags("RPG, cerveja; rpg | música") == ["rpg", "cerveja", "música"]


# ── build_candidates ─────────────────────────────────────────────


def test_build_candidates_uses_autodetect_when_mapping_missing():
    headers = ["Nome", "Telefone", "E-mail", "Aniversario", "Grupos"]
    rows = [
        {
            "Nome": "Ana",
            "Telefone": "11111",
            "E-mail": "ana@x.com",
            "Aniversario": "15/03/1990",
            "Grupos": "rpg, cerveja",
        }
    ]
    candidates, mapping = build_candidates(headers, rows)
    assert mapping["Nome"] == "name"
    assert mapping["Grupos"] == "tags"
    assert len(candidates) == 1
    c = candidates[0]
    assert c.name == "Ana"
    assert c.phone == "11111"
    assert c.email == "ana@x.com"
    assert c.birthday is not None and c.birthday.isoformat() == "1990-03-15"
    assert c.tags == ["rpg", "cerveja"]


def test_build_candidates_skips_rows_without_name():
    headers = ["Nome", "Telefone"]
    rows = [
        {"Nome": "", "Telefone": "11111"},
        {"Nome": "Bruno", "Telefone": "22222"},
    ]
    candidates, _ = build_candidates(headers, rows)
    assert [c.name for c in candidates] == ["Bruno"]
    # source_index reflete a posicao original, mas como pulamos o
    # primeiro, esperamos 1 (index do Bruno na lista de rows).
    assert candidates[0].source_index == 1


def test_build_candidates_respects_explicit_mapping_overriding_autodetect():
    headers = ["Coluna A", "Coluna B"]
    rows = [{"Coluna A": "Ana", "Coluna B": "tag1, tag2"}]
    mapping = {"Coluna A": "name", "Coluna B": "tags"}
    candidates, used = build_candidates(headers, rows, mapping)
    assert used == mapping
    assert candidates[0].name == "Ana"
    assert candidates[0].tags == ["tag1", "tag2"]


def test_build_candidates_first_value_wins_for_duplicate_field():
    headers = ["nome", "fone1", "fone2"]
    rows = [{"nome": "Ana", "fone1": "11111", "fone2": "22222"}]
    mapping = {"nome": "name", "fone1": "phone", "fone2": "phone"}
    candidates, _ = build_candidates(headers, rows, mapping)
    assert candidates[0].phone == "11111"


# ── preview_csv ──────────────────────────────────────────────────


def test_preview_csv_includes_suggested_mapping_and_total():
    text = "Nome,Telefone,Aniversario\nAna,11111,1990-03-15\n"
    preview = import_service.preview_csv(text)
    assert preview.total == 1
    assert preview.detected_fields == ["Nome", "Telefone", "Aniversario"]
    assert preview.suggested_mapping == {
        "Nome": "name",
        "Telefone": "phone",
        "Aniversario": "birthday",
    }


# ── Integration: HTTP endpoints ──────────────────────────────────


@pytest.mark.asyncio
async def test_csv_preview_endpoint_returns_preview(client):
    csv_bytes = b"Nome,Telefone\nAna,11111\nBruno,22222\n"
    response = await client.post(
        "/api/import/csv/preview",
        files={"file": ("contatos.csv", csv_bytes, "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["detected_fields"] == ["Nome", "Telefone"]
    assert body["suggested_mapping"] == {"Nome": "name", "Telefone": "phone"}
    assert [c["name"] for c in body["candidates"]] == ["Ana", "Bruno"]


@pytest.mark.asyncio
async def test_csv_preview_with_explicit_mapping(client):
    csv_bytes = b"col_a,col_b\nAna,whatever\n"
    mapping = json.dumps({"col_a": "name", "col_b": "ignore"})
    response = await client.post(
        "/api/import/csv/preview",
        files={"file": ("x.csv", csv_bytes, "text/csv")},
        data={"mapping": mapping},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["candidates"][0]["name"] == "Ana"
    assert body["suggested_mapping"] == {"col_a": "name", "col_b": "ignore"}


@pytest.mark.asyncio
async def test_csv_preview_invalid_mapping_json_returns_400(client):
    csv_bytes = b"name\nAna\n"
    response = await client.post(
        "/api/import/csv/preview",
        files={"file": ("x.csv", csv_bytes, "text/csv")},
        data={"mapping": "{not json"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_BAD_MAPPING"


@pytest.mark.asyncio
async def test_csv_commit_persists_only_approved_rows(client):
    csv_bytes = (
        b"Nome,Telefone,Aniversario,Tags\n"
        b"Ana,11111,1990-03-15,rpg\n"
        b"Bruno,22222,1985-07-20,cerveja\n"
        b"Carla,33333,1992-01-10,musica\n"
    )
    payload = json.dumps(
        {
            "approved_indexes": [0, 2],
            "default_category": "rekindle",
            "default_cadence": "monthly",
            "mapping": {
                "Nome": "name",
                "Telefone": "phone",
                "Aniversario": "birthday",
                "Tags": "tags",
            },
        }
    )
    response = await client.post(
        "/api/import/csv/commit",
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"payload": payload},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["imported"] == 2
    assert body["skipped"] == 0
    assert body["errors"] == []

    # Confirma persistencia: lista deve ter os dois aprovados.
    listed = await client.get("/api/friends")
    assert listed.status_code == 200
    names = sorted(f["name"] for f in listed.json())
    assert names == ["Ana", "Carla"]
    ana = next(f for f in listed.json() if f["name"] == "Ana")
    assert ana["phone"] == "11111"
    assert ana["birthday"] == "1990-03-15"
    assert ana["tags"] == ["rpg"]
    assert ana["cadence"] == "monthly"
    assert ana["category"] == "rekindle"


@pytest.mark.asyncio
async def test_csv_commit_skipped_index_returns_error_entry(client):
    csv_bytes = b"name,phone\nAna,11111\n"
    payload = json.dumps(
        {
            "approved_indexes": [0, 99],
            "default_category": "upgrade",
            "default_cadence": "weekly",
            "mapping": {"name": "name", "phone": "phone"},
        }
    )
    response = await client.post(
        "/api/import/csv/commit",
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"payload": payload},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["imported"] == 1
    assert body["skipped"] == 1
    assert any("99" in e for e in body["errors"])


@pytest.mark.asyncio
async def test_csv_commit_without_mapping_returns_error(client):
    csv_bytes = b"name\nAna\n"
    payload = json.dumps(
        {
            "approved_indexes": [0],
            "default_category": "upgrade",
            "default_cadence": "weekly",
        }
    )
    response = await client.post(
        "/api/import/csv/commit",
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"payload": payload},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_MAPPING_REQUIRED"


@pytest.mark.asyncio
async def test_csv_commit_empty_file_returns_error(client):
    csv_bytes = b""
    payload = json.dumps(
        {
            "approved_indexes": [],
            "default_category": "upgrade",
            "default_cadence": "weekly",
            "mapping": {},
        }
    )
    response = await client.post(
        "/api/import/csv/commit",
        files={"file": ("c.csv", csv_bytes, "text/csv")},
        data={"payload": payload},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "IMPORT_EMPTY_FILE"
