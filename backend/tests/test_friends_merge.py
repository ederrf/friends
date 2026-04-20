"""Testes do merge de amigos (13.22, acao adicional).

Cobertura:
- Happy path com 2+ sources: primary preservado, sources apagados,
  interactions migradas, tags unidas sem duplicata.
- last_contact_at fica com o max entre todos.
- Campos escalares vazios do primary sao preenchidos com 1o nao-vazio
  dos sources, na ordem.
- name/category/cadence do primary NAO sao sobrescritos.
- primary_id aparecendo dentro de source_ids e filtrado silenciosamente.
- source_id inexistente entra em not_found; zero sources validos nao
  deve afetar o primary.
- primary_id inexistente -> 404.
- Validacao basica do payload (source_ids vazio, primary_id 0).
"""

from __future__ import annotations


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


async def _register_interaction(
    client, friend_id: int, note: str, occurred_at: str
) -> dict:
    r = await client.post(
        f"/api/friends/{friend_id}/interactions",
        json={
            "note": note,
            "occurred_at": occurred_at,
            "interaction_type": "message",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Happy path ──────────────────────────────────────────────────


async def test_merge_funde_interactions_tags_e_deleta_sources(client):
    p = await _create(client, "Ana", tags=["rpg"])
    s1 = await _create(client, "Ana Silva", tags=["cerveja", "rpg"])
    s2 = await _create(client, "A. Silva", tags=["trabalho"])

    # 2 interactions em s1 + 1 em s2
    await _register_interaction(
        client, s1["id"], "oi", "2026-04-01T10:00:00-03:00"
    )
    await _register_interaction(
        client, s1["id"], "cafe", "2026-04-05T10:00:00-03:00"
    )
    await _register_interaction(
        client, s2["id"], "reuniao", "2026-04-10T10:00:00-03:00"
    )

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"], s2["id"]]},
    )
    assert r.status_code == 200, r.text
    body = r.json()

    # Resumo
    assert body["merged"] == 2
    assert body["not_found"] == []
    assert body["interactions_moved"] == 3
    # rpg ja estava no primary -> nao conta; cerveja + trabalho sao novas
    assert body["tags_added"] == 2

    merged = body["friend"]
    assert merged["id"] == p["id"]
    assert merged["name"] == "Ana"  # nome do primary preservado
    assert sorted(merged["tags"]) == ["cerveja", "rpg", "trabalho"]

    # Sources sumiram
    assert (await client.get(f"/api/friends/{s1['id']}")).status_code == 404
    assert (await client.get(f"/api/friends/{s2['id']}")).status_code == 404

    # Interactions todas estao no primary
    interactions = (
        await client.get(f"/api/friends/{p['id']}/interactions")
    ).json()
    assert len(interactions) == 3
    assert all(i["friend_id"] == p["id"] for i in interactions)


async def test_merge_preenche_campos_escalares_vazios_do_primary(client):
    # Primary sem phone/email; sources trazem os dados.
    p = await _create(client, "Ana")
    s1 = await _create(
        client,
        "Ana Silva",
        phone="(11) 99999-1111",
        email="ana.silva@example.com",
    )
    s2 = await _create(
        client,
        "A. Silva",
        phone="(11) 11111-2222",  # nao deve sobrescrever (s1 vem antes)
        email="a@example.com",
    )

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"], s2["id"]]},
    )
    assert r.status_code == 200
    merged = r.json()["friend"]
    # Primeiro nao-vazio vem do s1 (vem antes na lista)
    assert merged["phone"] == "(11) 99999-1111"
    assert merged["email"] == "ana.silva@example.com"


async def test_merge_nao_sobrescreve_campos_ja_preenchidos(client):
    p = await _create(
        client, "Ana", phone="(11) 55555-0000", email="ana@example.com"
    )
    s1 = await _create(
        client, "Ana 2", phone="(11) 99999-1111", email="other@example.com"
    )

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"]]},
    )
    assert r.status_code == 200
    merged = r.json()["friend"]
    assert merged["phone"] == "(11) 55555-0000"
    assert merged["email"] == "ana@example.com"


async def test_merge_preserva_name_category_cadence_do_primary(client):
    p = await _create(
        client, "Ana", category="maintain", cadence="monthly"
    )
    s1 = await _create(
        client, "Ana Silva", category="rekindle", cadence="weekly"
    )
    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"]]},
    )
    assert r.status_code == 200
    merged = r.json()["friend"]
    assert merged["name"] == "Ana"
    assert merged["category"] == "maintain"
    assert merged["cadence"] == "monthly"


async def test_merge_last_contact_at_fica_com_o_max(client):
    p = await _create(client, "Ana")
    s1 = await _create(client, "Ana Silva")

    # Interaction recente em s1 => vira last_contact_at do primary apos merge
    await _register_interaction(
        client, s1["id"], "recente", "2026-04-15T10:00:00-03:00"
    )
    # Interaction mais antiga direto no primary
    await _register_interaction(
        client, p["id"], "antiga", "2026-01-01T10:00:00-03:00"
    )

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"]]},
    )
    assert r.status_code == 200
    merged = r.json()["friend"]
    assert merged["last_contact_at"].startswith("2026-04-15")


# ── Edge cases ──────────────────────────────────────────────────


async def test_merge_primary_dentro_de_source_ids_e_filtrado(client):
    p = await _create(client, "Ana")
    s1 = await _create(client, "Ana Silva")

    r = await client.post(
        "/api/friends/bulk/merge",
        json={
            "primary_id": p["id"],
            "source_ids": [p["id"], s1["id"], p["id"]],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"] == 1  # so s1 fundido
    assert body["not_found"] == []
    assert (await client.get(f"/api/friends/{p['id']}")).status_code == 200


async def test_merge_source_inexistente_vai_pra_not_found(client):
    p = await _create(client, "Ana")
    s1 = await _create(client, "Ana Silva")

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"], 99999]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"] == 1
    assert body["not_found"] == [99999]


async def test_merge_sem_sources_validos_e_no_op(client):
    p = await _create(client, "Ana")
    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [99998, 99999]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"] == 0
    assert sorted(body["not_found"]) == [99998, 99999]
    assert body["interactions_moved"] == 0
    assert body["tags_added"] == 0


async def test_merge_primary_inexistente_404(client):
    s1 = await _create(client, "Ana")
    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": 99999, "source_ids": [s1["id"]]},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FRIEND_NOT_FOUND"


async def test_merge_source_ids_vazio_400(client):
    p = await _create(client, "Ana")
    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": []},
    )
    assert r.status_code == 400


async def test_merge_primary_id_zero_400(client):
    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": 0, "source_ids": [1]},
    )
    assert r.status_code == 400


async def test_merge_idempotencia_de_tags_em_colisao(client):
    """Unique (friend_id, tag) nao pode quebrar quando o source tem tag que
    o primary ja possui."""
    p = await _create(client, "Ana", tags=["rpg", "cerveja"])
    s1 = await _create(client, "Ana Silva", tags=["rpg", "trabalho"])

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": p["id"], "source_ids": [s1["id"]]},
    )
    assert r.status_code == 200
    merged = r.json()["friend"]
    # rpg nao duplica; cerveja do primary fica; trabalho do source entra
    assert sorted(merged["tags"]) == ["cerveja", "rpg", "trabalho"]
    assert r.json()["tags_added"] == 1  # so trabalho foi adicionada
