"""Testes de integracao dos routers de interesses e tags (13.9)."""

from __future__ import annotations

import pytest_asyncio


def _payload(name: str, **overrides) -> dict:
    base = {
        "name": name,
        "category": "rekindle",
        "cadence": "monthly",
        "tags": [],
    }
    base.update(overrides)
    return base


@pytest_asyncio.fixture
async def friend_id(client) -> int:
    r = await client.post("/api/friends", json=_payload("Ana"))
    return r.json()["id"]


# ── GET /api/interests ──────────────────────────────────────────


async def test_list_interests_vazio(client):
    r = await client.get("/api/interests")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_interests_conta_amigos_por_tag(client):
    await client.post("/api/friends", json=_payload("Ana", tags=["rpg", "cinema"]))
    await client.post("/api/friends", json=_payload("Bruno", tags=["rpg"]))
    await client.post("/api/friends", json=_payload("Carla", tags=["cinema"]))

    r = await client.get("/api/interests")
    body = r.json()
    as_map = {item["tag"]: item["friend_count"] for item in body}
    assert as_map == {"rpg": 2, "cinema": 2}


async def test_list_interests_inclui_tags_solo(client):
    """Diferente de /dashboard/clusters, aqui tags com 1 amigo aparecem."""
    await client.post("/api/friends", json=_payload("Ana", tags=["solo"]))
    r = await client.get("/api/interests")
    assert r.json() == [{"tag": "solo", "friend_count": 1}]


async def test_list_interests_ordena_por_contagem_desc(client):
    await client.post("/api/friends", json=_payload("A", tags=["popular"]))
    await client.post("/api/friends", json=_payload("B", tags=["popular"]))
    await client.post("/api/friends", json=_payload("C", tags=["popular", "nicho"]))
    r = await client.get("/api/interests")
    tags = [i["tag"] for i in r.json()]
    assert tags == ["popular", "nicho"]


# ── POST /api/friends/{id}/tags ─────────────────────────────────


async def test_add_tag_feliz(client, friend_id):
    r = await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "Cerveja"})
    assert r.status_code == 201, r.text
    body = r.json()
    # normalizada para lowercase
    assert "cerveja" in body["tags"]


async def test_add_tag_dedup_normalizada(client, friend_id):
    await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "rpg"})
    r = await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "RPG"})
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "TAG_ALREADY_EXISTS"
    assert body["error"]["details"]["tag"] == "rpg"


async def test_add_tag_vazia_apos_strip(client, friend_id):
    r = await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "   "})
    # schema rejeita antes (min_length=1 nao exige nao-whitespace, entao
    # o servico e quem marca como invalida)
    assert r.status_code in (400, 409)


async def test_add_tag_friend_inexistente(client):
    r = await client.post("/api/friends/9999/tags", json={"tag": "rpg"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"


async def test_add_tag_payload_invalido(client, friend_id):
    r = await client.post(f"/api/friends/{friend_id}/tags", json={"tag": ""})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


# ── DELETE /api/friends/{id}/tags/{tag} ─────────────────────────


async def test_remove_tag_feliz(client, friend_id):
    await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "rpg"})
    r = await client.delete(f"/api/friends/{friend_id}/tags/rpg")
    assert r.status_code == 200
    body = r.json()
    assert "rpg" not in body["tags"]


async def test_remove_tag_normaliza_input(client, friend_id):
    await client.post(f"/api/friends/{friend_id}/tags", json={"tag": "cinema"})
    # DELETE passando caixa alta deve normalizar e remover
    r = await client.delete(f"/api/friends/{friend_id}/tags/CINEMA")
    assert r.status_code == 200
    assert "cinema" not in r.json()["tags"]


async def test_remove_tag_inexistente_retorna_404(client, friend_id):
    r = await client.delete(f"/api/friends/{friend_id}/tags/inexistente")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "TAG_NOT_FOUND"


async def test_remove_tag_friend_inexistente(client):
    r = await client.delete("/api/friends/9999/tags/rpg")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"
