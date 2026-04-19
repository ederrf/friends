"""Testes de integracao do router de dashboard (13.8)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _make_payload(name: str, **overrides) -> dict:
    base = {
        "name": name,
        "category": "rekindle",
        "cadence": "monthly",
        "tags": [],
    }
    base.update(overrides)
    return base


async def test_summary_banco_vazio(client):
    r = await client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "total_friends": 0,
        "overdue_count": 0,
        "total_interests": 0,
        "average_temperature": 0,
        "friends_by_temperature": [],
        "overdue_friends": [],
    }


async def test_summary_conta_totais_e_interesses(client):
    await client.post("/api/friends", json=_make_payload("Ana", tags=["rpg", "cinema"]))
    await client.post(
        "/api/friends", json=_make_payload("Bruno", tags=["RPG", "futebol"])
    )
    await client.post("/api/friends", json=_make_payload("Carla", tags=["cinema"]))

    r = await client.get("/api/dashboard/summary")
    body = r.json()
    assert body["total_friends"] == 3
    # tags normalizadas: rpg, cinema, futebol = 3 interesses unicos
    assert body["total_interests"] == 3
    # nenhum deles tem last_contact_at -> todos quentes, media alta
    assert body["average_temperature"] >= 80


async def test_summary_overdue_identifica_atrasados(client):
    # amigo criado + interacao muito antiga -> next_ping negativo
    r = await client.post("/api/friends", json=_make_payload("Antigo"))
    friend_id = r.json()["id"]
    old = (datetime.now(timezone.utc) - timedelta(days=120)).replace(microsecond=0)
    await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"occurred_at": old.isoformat()},
    )
    # amigo recem-criado sem atraso (usa created_at como fallback)
    await client.post("/api/friends", json=_make_payload("NovoEmFolha"))

    r = await client.get("/api/dashboard/summary")
    body = r.json()
    assert body["overdue_count"] == 1
    assert [f["name"] for f in body["overdue_friends"]] == ["Antigo"]


async def test_summary_ordena_por_temperatura_desc(client):
    # quente (sem contato, usa created_at) e frio (contato antigo)
    await client.post("/api/friends", json=_make_payload("Quente"))
    r = await client.post("/api/friends", json=_make_payload("Frio"))
    frio_id = r.json()["id"]
    old = (datetime.now(timezone.utc) - timedelta(days=200)).replace(microsecond=0)
    await client.post(
        f"/api/friends/{frio_id}/interactions",
        json={"occurred_at": old.isoformat()},
    )

    r = await client.get("/api/dashboard/summary")
    ordem = [f["name"] for f in r.json()["friends_by_temperature"]]
    assert ordem.index("Quente") < ordem.index("Frio")


async def test_overdue_endpoint(client):
    r = await client.post("/api/friends", json=_make_payload("Atrasado"))
    friend_id = r.json()["id"]
    old = (datetime.now(timezone.utc) - timedelta(days=90)).replace(microsecond=0)
    await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"occurred_at": old.isoformat()},
    )
    await client.post("/api/friends", json=_make_payload("EmDia"))

    r = await client.get("/api/dashboard/overdue")
    assert r.status_code == 200
    names = [f["name"] for f in r.json()["friends"]]
    assert names == ["Atrasado"]


async def test_overdue_vazio(client):
    await client.post("/api/friends", json=_make_payload("Novo"))
    r = await client.get("/api/dashboard/overdue")
    assert r.json() == {"friends": []}


async def test_clusters_agrupa_por_tag_compartilhada(client):
    # 2 amigos compartilham "rpg"; "cinema" tambem compartilhada; "solo" nao vira cluster
    await client.post("/api/friends", json=_make_payload("Ana", tags=["rpg", "cinema"]))
    await client.post("/api/friends", json=_make_payload("Bruno", tags=["rpg"]))
    await client.post("/api/friends", json=_make_payload("Carla", tags=["cinema"]))
    await client.post("/api/friends", json=_make_payload("Dino", tags=["solo"]))

    r = await client.get("/api/dashboard/clusters")
    body = r.json()
    tags_retornadas = [c["tag"] for c in body["clusters"]]
    # rpg e cinema viram clusters (>=2); solo e ignorado
    assert set(tags_retornadas) == {"rpg", "cinema"}
    # ordenacao por tamanho desc: rpg e cinema tem 2 cada -> desempate alfabetico
    assert tags_retornadas == ["cinema", "rpg"]

    # amigos dentro do cluster "rpg"
    rpg = next(c for c in body["clusters"] if c["tag"] == "rpg")
    assert [f["name"] for f in rpg["friends"]] == ["Ana", "Bruno"]


async def test_clusters_vazio_quando_nao_ha_compartilhamento(client):
    await client.post("/api/friends", json=_make_payload("Ana", tags=["rpg"]))
    await client.post("/api/friends", json=_make_payload("Bruno", tags=["cinema"]))
    r = await client.get("/api/dashboard/clusters")
    assert r.json() == {"clusters": []}


async def test_summary_tags_normalizadas_nao_inflam_interesses(client):
    """`RPG` e `rpg` devem contar como 1 interesse."""
    await client.post("/api/friends", json=_make_payload("Ana", tags=["RPG"]))
    await client.post("/api/friends", json=_make_payload("Bruno", tags=["rpg"]))
    r = await client.get("/api/dashboard/summary")
    assert r.json()["total_interests"] == 1
