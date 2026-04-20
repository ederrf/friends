"""Testes dos endpoints de bulk actions em amigos (13.22).

Cobertura:
- bulk delete: happy path, not_found silencioso, cascade de tags/interactions,
  ids duplicados no payload sao deduplicados, erro de schema (lista vazia).
- bulk touch: happy path (temperatura vai para Quente), not_found misturado
  com ok, payload validado.
- bulk add tag: normalizacao (lower+strip), skipped para quem ja tem,
  not_found, tag vazia -> 409 TAG_INVALID.
- bulk remove tag: remocao em massa, skipped para quem nao tinha.
"""

from __future__ import annotations

import pytest

from app.models.friend import Friend
from app.models.friend_tag import FriendTag


# ── Helpers ──────────────────────────────────────────────────────


async def _create(client, name: str, **overrides) -> dict:
    payload = {
        "name": name,
        "category": "rekindle",
        "cadence": "monthly",
        "tags": [],
        **overrides,
    }
    r = await client.post("/api/friends", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ── Bulk delete ──────────────────────────────────────────────────


async def test_bulk_delete_happy_path(client):
    a = await _create(client, "Ana")
    b = await _create(client, "Bruno")
    c = await _create(client, "Carla")

    r = await client.post(
        "/api/friends/bulk/delete", json={"ids": [a["id"], b["id"]]}
    )
    assert r.status_code == 200
    assert r.json() == {"affected": 2, "not_found": [], "skipped": []}

    # Carla ainda existe
    remaining = (await client.get("/api/friends")).json()
    assert [f["id"] for f in remaining] == [c["id"]]


async def test_bulk_delete_ids_inexistentes_vao_para_not_found(client):
    a = await _create(client, "Ana")

    r = await client.post(
        "/api/friends/bulk/delete", json={"ids": [a["id"], 9999, 8888]}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 1
    assert sorted(body["not_found"]) == [8888, 9999]


async def test_bulk_delete_dedup_ids_no_payload(client):
    a = await _create(client, "Ana")
    r = await client.post(
        "/api/friends/bulk/delete", json={"ids": [a["id"], a["id"], a["id"]]}
    )
    assert r.status_code == 200
    # mesmo id 3x no payload => afeta 1 (dedupe) e nao aparece em not_found
    assert r.json() == {"affected": 1, "not_found": [], "skipped": []}


async def test_bulk_delete_cascade_tags(client, session):
    """Apagar amigo apaga FriendTag em cascata (model config)."""
    a = await _create(client, "Ana", tags=["rpg", "cerveja"])

    # confirma que as tags foram gravadas
    pre = await session.execute(
        FriendTag.__table__.select().where(FriendTag.friend_id == a["id"])
    )
    assert len(pre.all()) == 2

    r = await client.post("/api/friends/bulk/delete", json={"ids": [a["id"]]})
    assert r.status_code == 200

    post = await session.execute(
        FriendTag.__table__.select().where(FriendTag.friend_id == a["id"])
    )
    assert post.all() == []


async def test_bulk_delete_lista_vazia_422(client):
    r = await client.post("/api/friends/bulk/delete", json={"ids": []})
    assert r.status_code == 400


async def test_bulk_delete_acima_do_limite_422(client):
    r = await client.post(
        "/api/friends/bulk/delete", json={"ids": list(range(1, 502))}
    )
    assert r.status_code == 400


# ── Bulk touch ───────────────────────────────────────────────────


async def test_bulk_touch_eleva_temperatura_a_quente(client):
    # Amigo com cadencia weekly vai ter temperatura dependente dos dias.
    # Depois do touch, last_contact_at = agora => temperatura = 100 (Quente).
    a = await _create(client, "Ana", cadence="weekly")

    r = await client.post("/api/friends/bulk/touch", json={"ids": [a["id"]]})
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 1
    assert body["not_found"] == []

    reloaded = (await client.get(f"/api/friends/{a['id']}")).json()
    assert reloaded["temperature"] == 100
    assert reloaded["temperature_label"] == "Quente"
    assert reloaded["last_contact_at"] is not None


async def test_bulk_touch_mistura_ok_e_not_found(client):
    a = await _create(client, "Ana")

    r = await client.post(
        "/api/friends/bulk/touch", json={"ids": [a["id"], 77777]}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 1
    assert body["not_found"] == [77777]


async def test_bulk_touch_lista_vazia_422(client):
    r = await client.post("/api/friends/bulk/touch", json={"ids": []})
    assert r.status_code == 400


# ── Bulk add tag ─────────────────────────────────────────────────


async def test_bulk_add_tag_happy_path(client):
    a = await _create(client, "Ana")
    b = await _create(client, "Bruno")

    r = await client.post(
        "/api/friends/bulk/tags/add",
        json={"ids": [a["id"], b["id"]], "tag": "importado"},
    )
    assert r.status_code == 200
    assert r.json() == {"affected": 2, "not_found": [], "skipped": []}

    for fid in (a["id"], b["id"]):
        reloaded = (await client.get(f"/api/friends/{fid}")).json()
        assert reloaded["tags"] == ["importado"]


async def test_bulk_add_tag_normaliza_case_e_espacos(client):
    a = await _create(client, "Ana")

    r = await client.post(
        "/api/friends/bulk/tags/add",
        json={"ids": [a["id"]], "tag": "  RPG  "},
    )
    assert r.status_code == 200
    reloaded = (await client.get(f"/api/friends/{a['id']}")).json()
    assert reloaded["tags"] == ["rpg"]


async def test_bulk_add_tag_skipped_quando_ja_tem(client):
    a = await _create(client, "Ana", tags=["rpg"])
    b = await _create(client, "Bruno")

    r = await client.post(
        "/api/friends/bulk/tags/add",
        json={"ids": [a["id"], b["id"]], "tag": "rpg"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 1  # so o Bruno ganhou
    assert body["skipped"] == [a["id"]]
    assert body["not_found"] == []


async def test_bulk_add_tag_not_found_em_ids_invalidos(client):
    a = await _create(client, "Ana")

    r = await client.post(
        "/api/friends/bulk/tags/add",
        json={"ids": [a["id"], 54321], "tag": "novo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 1
    assert body["not_found"] == [54321]


async def test_bulk_add_tag_vazia_409(client):
    a = await _create(client, "Ana")
    r = await client.post(
        "/api/friends/bulk/tags/add",
        json={"ids": [a["id"]], "tag": "   "},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "TAG_INVALID"


# ── Bulk remove tag ──────────────────────────────────────────────


async def test_bulk_remove_tag_happy_path(client):
    a = await _create(client, "Ana", tags=["rpg", "cerveja"])
    b = await _create(client, "Bruno", tags=["rpg"])
    c = await _create(client, "Carla")  # nao tem a tag

    r = await client.post(
        "/api/friends/bulk/tags/remove",
        json={"ids": [a["id"], b["id"], c["id"]], "tag": "rpg"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 2
    assert body["skipped"] == [c["id"]]
    assert body["not_found"] == []

    # rpg sumiu de a e b; cerveja segue com a
    ana = (await client.get(f"/api/friends/{a['id']}")).json()
    assert ana["tags"] == ["cerveja"]
    bruno = (await client.get(f"/api/friends/{b['id']}")).json()
    assert bruno["tags"] == []


async def test_bulk_remove_tag_not_found_silencioso(client):
    r = await client.post(
        "/api/friends/bulk/tags/remove",
        json={"ids": [9999], "tag": "rpg"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {"affected": 0, "not_found": [9999], "skipped": []}
