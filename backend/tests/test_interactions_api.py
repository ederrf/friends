"""Testes de integracao do router de interacoes (13.7)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest_asyncio


@pytest_asyncio.fixture
async def friend_id(client, friend_payload) -> int:
    """Cria um amigo e devolve o id — reutilizado na maioria dos testes."""
    created = (await client.post("/api/friends", json=friend_payload)).json()
    return created["id"]


async def test_list_interactions_vazia(client, friend_id):
    r = await client.get(f"/api/friends/{friend_id}/interactions")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_interactions_friend_inexistente(client):
    r = await client.get("/api/friends/9999/interactions")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"


async def test_create_interaction_happy_path(client, friend_id):
    r = await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"note": "Tomamos um cafe", "interaction_type": "in_person"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["id"] > 0
    assert body["friend_id"] == friend_id
    assert body["note"] == "Tomamos um cafe"
    assert body["interaction_type"] == "in_person"
    # occurred_at ausente no payload deve ser preenchido pelo servico
    assert body["occurred_at"] is not None


async def test_create_interaction_sem_campos(client, friend_id):
    """Payload minimo: tudo opcional, interaction_type default = other."""
    r = await client.post(f"/api/friends/{friend_id}/interactions", json={})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["interaction_type"] == "other"
    assert body["note"] is None


async def test_create_interaction_atualiza_last_contact(client, friend_id):
    # amigo recem-criado: last_contact_at comeca None
    before = (await client.get(f"/api/friends/{friend_id}")).json()
    assert before["last_contact_at"] is None

    now = datetime.now(timezone.utc).replace(microsecond=0)
    r = await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"occurred_at": now.isoformat(), "interaction_type": "call"},
    )
    assert r.status_code == 201

    after = (await client.get(f"/api/friends/{friend_id}")).json()
    assert after["last_contact_at"] is not None
    # days_since_last_contact deve voltar para ~0 apos registro
    assert after["days_since_last_contact"] == 0


async def test_last_contact_so_avanca(client, friend_id):
    """Interacao historica (mais antiga) nao rebaixa last_contact_at."""
    recent = datetime.now(timezone.utc).replace(microsecond=0)
    old = recent - timedelta(days=30)

    # primeiro registra a recente
    await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"occurred_at": recent.isoformat(), "interaction_type": "message"},
    )
    snap_recent = (await client.get(f"/api/friends/{friend_id}")).json()

    # depois registra uma historica
    await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"occurred_at": old.isoformat(), "interaction_type": "message"},
    )
    snap_after_old = (await client.get(f"/api/friends/{friend_id}")).json()

    # last_contact_at nao regride
    assert snap_recent["last_contact_at"] == snap_after_old["last_contact_at"]
    assert snap_after_old["days_since_last_contact"] == 0


async def test_list_interactions_ordenada_por_data_desc(client, friend_id):
    base = datetime.now(timezone.utc).replace(microsecond=0)
    t1 = base - timedelta(days=10)
    t2 = base - timedelta(days=5)
    t3 = base  # mais recente

    for ts, note in [(t1, "A"), (t3, "C"), (t2, "B")]:
        await client.post(
            f"/api/friends/{friend_id}/interactions",
            json={"occurred_at": ts.isoformat(), "note": note},
        )

    r = await client.get(f"/api/friends/{friend_id}/interactions")
    notes = [i["note"] for i in r.json()]
    assert notes == ["C", "B", "A"]


async def test_create_interaction_friend_inexistente(client):
    r = await client.post("/api/friends/9999/interactions", json={"note": "x"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"


async def test_create_interaction_tipo_invalido(client, friend_id):
    r = await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"interaction_type": "telepathy"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_create_interaction_nota_grande_rejeitada(client, friend_id):
    r = await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={"note": "x" * 2001},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_delete_friend_apaga_interacoes(client, friend_id):
    await client.post(f"/api/friends/{friend_id}/interactions", json={"note": "x"})
    await client.delete(f"/api/friends/{friend_id}")
    # amigo vai: lista deve dar 404 pelo friend inexistente
    r = await client.get(f"/api/friends/{friend_id}/interactions")
    assert r.status_code == 404
