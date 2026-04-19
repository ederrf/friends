"""Testes de integracao do router de amigos (13.6)."""

from __future__ import annotations

import pytest


async def test_list_vazia(client):
    r = await client.get("/api/friends")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_friend_happy_path(client, friend_payload):
    r = await client.post("/api/friends", json=friend_payload)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["name"] == "Marcelo Silva"
    assert body["category"] == "rekindle"
    assert body["cadence"] == "monthly"
    # tags normalizadas (lowercase) e sem duplicata
    assert body["tags"] == ["cerveja", "rpg"]
    # metricas derivadas devem vir preenchidas
    assert body["temperature"] >= 0
    assert body["temperature_label"] in {"Quente", "Morna", "Esfriando", "Fria"}
    assert isinstance(body["days_since_last_contact"], int)
    assert isinstance(body["days_until_next_ping"], int)


async def test_get_friend_por_id(client, friend_payload):
    created = (await client.post("/api/friends", json=friend_payload)).json()
    r = await client.get(f"/api/friends/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


async def test_get_friend_404_formato_padrao(client):
    r = await client.get("/api/friends/9999")
    assert r.status_code == 404
    body = r.json()
    assert body == {
        "error": {
            "code": "FRIEND_NOT_FOUND",
            "message": "friend 9999 nao encontrado.",
            "details": {"entity": "friend", "id": 9999},
        }
    }


async def test_patch_friend_atualizacao_parcial(client, friend_payload):
    created = (await client.post("/api/friends", json=friend_payload)).json()
    r = await client.patch(
        f"/api/friends/{created['id']}",
        json={"cadence": "weekly", "notes": "novo resumo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["cadence"] == "weekly"
    assert body["notes"] == "novo resumo"
    # campos nao enviados permanecem
    assert body["name"] == "Marcelo Silva"
    assert body["category"] == "rekindle"


async def test_patch_friend_404(client):
    r = await client.patch("/api/friends/123", json={"notes": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"


async def test_delete_friend(client, friend_payload):
    created = (await client.post("/api/friends", json=friend_payload)).json()
    r = await client.delete(f"/api/friends/{created['id']}")
    assert r.status_code == 204
    r2 = await client.get(f"/api/friends/{created['id']}")
    assert r2.status_code == 404


async def test_delete_friend_404(client):
    r = await client.delete("/api/friends/999")
    assert r.status_code == 404


async def test_validacao_formato_padrao(client):
    # category invalida deve virar 400 com code VALIDATION_ERROR
    r = await client.post(
        "/api/friends",
        json={
            "name": "x",
            "category": "invalid_category",
            "cadence": "monthly",
        },
    )
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "errors" in body["error"]["details"]


async def test_filtros_list(client):
    # cria 3 amigos variados
    base = {
        "name": "A",
        "category": "rekindle",
        "cadence": "monthly",
        "tags": ["cinema"],
    }
    await client.post("/api/friends", json={**base, "name": "Ana"})
    await client.post(
        "/api/friends",
        json={**base, "name": "Bruno", "category": "maintain", "tags": ["futebol"]},
    )
    await client.post(
        "/api/friends",
        json={**base, "name": "Carla", "cadence": "weekly", "tags": ["cinema", "rpg"]},
    )

    # filtro por categoria
    r = await client.get("/api/friends", params={"category": "rekindle"})
    assert {f["name"] for f in r.json()} == {"Ana", "Carla"}

    # filtro por cadencia
    r = await client.get("/api/friends", params={"cadence": "weekly"})
    assert [f["name"] for f in r.json()] == ["Carla"]

    # filtro por tag (case-insensitive via normalizacao)
    r = await client.get("/api/friends", params={"tag": "CINEMA"})
    assert {f["name"] for f in r.json()} == {"Ana", "Carla"}


async def test_list_ordenada_por_nome(client, friend_payload):
    await client.post("/api/friends", json={**friend_payload, "name": "Zelda"})
    await client.post("/api/friends", json={**friend_payload, "name": "Ana"})
    await client.post("/api/friends", json={**friend_payload, "name": "Marcos"})
    r = await client.get("/api/friends")
    assert [f["name"] for f in r.json()] == ["Ana", "Marcos", "Zelda"]


async def test_create_aceita_sem_campos_opcionais(client):
    r = await client.post(
        "/api/friends",
        json={"name": "Minimal", "category": "upgrade", "cadence": "quarterly"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["phone"] is None
    assert body["email"] is None
    assert body["birthday"] is None
    assert body["tags"] == []
    assert body["last_contact_at"] is None


@pytest.mark.parametrize(
    "bad_payload, reason",
    [
        ({"name": "", "category": "rekindle", "cadence": "monthly"}, "nome vazio"),
        ({"name": "x", "category": "rekindle", "cadence": "invalida"}, "cadencia invalida"),
        (
            {"name": "x", "category": "rekindle", "cadence": "monthly", "email": "nao-eh-email"},
            "email invalido",
        ),
    ],
)
async def test_create_rejeita_payloads_invalidos(client, bad_payload, reason):
    r = await client.post("/api/friends", json=bad_payload)
    assert r.status_code == 400, f"falhou em: {reason}"
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
