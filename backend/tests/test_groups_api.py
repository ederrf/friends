"""Testes dos endpoints de grupos (13.23).

Cobertura:
- CRUD: create (com/sem descricao/cor), validacao (nome vazio, cor invalida,
  name_taken case-insensitive), get/list com member_count, update, delete
  com cascade de memberships.
- Membership: add/remove singular, list_members hidratado, 404 em grupo
  ou amigo inexistente, idempotencia de add.
- Bulk: add/remove em lote, dedupe, skipped, not_found, grupo 404, valida
  schema (lista vazia).
- Friends API: filtro `group_id`, FriendRead inclui `groups`, bulk add/remove
  via `/api/friends/bulk/groups/add|remove`.
- Merge + groups: memberships dos sources migram pro primary, colisoes
  deduplicadas.
"""

from __future__ import annotations


# ── Helpers ──────────────────────────────────────────────────────


async def _create_friend(client, name: str, **overrides) -> dict:
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


async def _create_group(client, name: str, **overrides) -> dict:
    payload = {"name": name, **overrides}
    r = await client.post("/api/groups", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD grupo ────────────────────────────────────────────────────


async def test_create_group_default_color(client):
    r = await client.post("/api/groups", json={"name": "Familia"})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Familia"
    assert body["color"] == "#64748b"  # default slate-500
    assert body["description"] is None
    assert body["member_count"] == 0


async def test_create_group_com_descricao_e_cor(client):
    r = await client.post(
        "/api/groups",
        json={
            "name": "RPG",
            "description": "Mesa de quarta-feira",
            "color": "#F59E0B",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["description"] == "Mesa de quarta-feira"
    # color e normalizada para lowercase
    assert body["color"] == "#f59e0b"


async def test_create_group_nome_colision_case_insensitive(client):
    await _create_group(client, "Trabalho")
    r = await client.post("/api/groups", json={"name": "TRABALHO"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "GROUP_NAME_TAKEN"


async def test_create_group_cor_invalida_400(client):
    # Formato errado -> ValidationError -> 400 (via handler custom).
    r = await client.post(
        "/api/groups", json={"name": "X", "color": "azul"}
    )
    assert r.status_code == 400


async def test_create_group_nome_vazio_400(client):
    r = await client.post("/api/groups", json={"name": "   "})
    assert r.status_code == 400


async def test_list_groups_ordenado_por_nome_com_count(client):
    await _create_group(client, "Zulu")
    await _create_group(client, "Alfa")
    g_mid = await _create_group(client, "Mike")
    # Adiciona 2 amigos ao grupo do meio
    a = await _create_friend(client, "Ana")
    b = await _create_friend(client, "Bruno")
    await client.post(
        f"/api/groups/{g_mid['id']}/members", json={"friend_id": a["id"]}
    )
    await client.post(
        f"/api/groups/{g_mid['id']}/members", json={"friend_id": b["id"]}
    )

    r = await client.get("/api/groups")
    assert r.status_code == 200
    names = [g["name"] for g in r.json()]
    assert names == ["Alfa", "Mike", "Zulu"]
    mike = next(g for g in r.json() if g["name"] == "Mike")
    assert mike["member_count"] == 2


async def test_get_group_inexistente_404(client):
    r = await client.get("/api/groups/9999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "GROUP_NOT_FOUND"


async def test_update_group_nome_color_descricao(client):
    g = await _create_group(client, "Antigo")
    r = await client.patch(
        f"/api/groups/{g['id']}",
        json={"name": "Novo", "color": "#10B981", "description": "ok"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Novo"
    assert body["color"] == "#10b981"
    assert body["description"] == "ok"


async def test_update_group_mesmo_nome_nao_colide_consigo(client):
    g = await _create_group(client, "Familia")
    r = await client.patch(
        f"/api/groups/{g['id']}", json={"name": "Familia", "color": "#ef4444"}
    )
    assert r.status_code == 200


async def test_update_group_colidindo_com_outro_409(client):
    await _create_group(client, "Familia")
    outro = await _create_group(client, "Outro")
    r = await client.patch(
        f"/api/groups/{outro['id']}", json={"name": "FAMILIA"}
    )
    assert r.status_code == 409


async def test_delete_group_cascade_memberships(client):
    g = await _create_group(client, "Temp")
    a = await _create_friend(client, "Ana")
    await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )

    r = await client.delete(f"/api/groups/{g['id']}")
    assert r.status_code == 204

    # Amigo continua existindo, mas sem o grupo
    r2 = await client.get(f"/api/friends/{a['id']}")
    assert r2.status_code == 200
    assert r2.json()["groups"] == []


# ── Membership ──────────────────────────────────────────────────


async def test_add_member_e_list(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")

    r = await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )
    assert r.status_code == 204

    # List members devolve FriendRead com grupos hidratados
    r = await client.get(f"/api/groups/{g['id']}/members")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Ana"
    assert [grp["name"] for grp in body[0]["groups"]] == ["RPG"]


async def test_add_member_idempotente(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")

    r = await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )
    assert r.status_code == 204

    # Adicionar de novo e no-op (sem erro, sem duplicar)
    r = await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )
    assert r.status_code == 204

    r = await client.get(f"/api/groups/{g['id']}")
    assert r.json()["member_count"] == 1


async def test_add_member_grupo_404(client):
    a = await _create_friend(client, "Ana")
    r = await client.post(
        "/api/groups/9999/members", json={"friend_id": a["id"]}
    )
    assert r.status_code == 404


async def test_add_member_amigo_404(client):
    g = await _create_group(client, "RPG")
    r = await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": 9999}
    )
    assert r.status_code == 404


async def test_remove_member(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )

    r = await client.delete(f"/api/groups/{g['id']}/members/{a['id']}")
    assert r.status_code == 204

    r = await client.get(f"/api/groups/{g['id']}/members")
    assert r.json() == []


async def test_remove_member_nao_membro_404(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    r = await client.delete(f"/api/groups/{g['id']}/members/{a['id']}")
    assert r.status_code == 404


# ── Bulk ─────────────────────────────────────────────────────────


async def test_bulk_add_members(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    b = await _create_friend(client, "Bruno")

    r = await client.post(
        f"/api/groups/{g['id']}/members/bulk/add",
        json={"friend_ids": [a["id"], b["id"], 9999]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["affected"] == 2
    assert body["not_found"] == [9999]
    assert body["skipped"] == []


async def test_bulk_add_members_dedupe_e_ja_membro(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    # Ja membro
    await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )
    b = await _create_friend(client, "Bruno")

    r = await client.post(
        f"/api/groups/{g['id']}/members/bulk/add",
        json={"friend_ids": [a["id"], a["id"], b["id"]]},
    )
    assert r.status_code == 200
    body = r.json()
    # a ja era membro (skipped), b foi adicionado
    assert body["affected"] == 1
    assert body["skipped"] == [a["id"]]
    assert body["not_found"] == []


async def test_bulk_remove_members(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    b = await _create_friend(client, "Bruno")
    c = await _create_friend(client, "Carla")
    for fid in (a["id"], b["id"]):
        await client.post(
            f"/api/groups/{g['id']}/members", json={"friend_id": fid}
        )

    r = await client.post(
        f"/api/groups/{g['id']}/members/bulk/remove",
        json={"friend_ids": [a["id"], b["id"], c["id"]]},
    )
    assert r.status_code == 200
    body = r.json()
    # c existe mas nao era membro -> skipped
    assert body["affected"] == 2
    assert body["skipped"] == [c["id"]]


async def test_bulk_grupo_404(client):
    a = await _create_friend(client, "Ana")
    r = await client.post(
        "/api/groups/9999/members/bulk/add",
        json={"friend_ids": [a["id"]]},
    )
    assert r.status_code == 404


async def test_bulk_lista_vazia_400(client):
    g = await _create_group(client, "RPG")
    r = await client.post(
        f"/api/groups/{g['id']}/members/bulk/add",
        json={"friend_ids": []},
    )
    assert r.status_code == 400


# ── Friends API integration ─────────────────────────────────────


async def test_friend_read_inclui_groups(client):
    g = await _create_group(client, "RPG", color="#F59E0B")
    a = await _create_friend(client, "Ana")
    await client.post(
        f"/api/groups/{g['id']}/members", json={"friend_id": a["id"]}
    )

    r = await client.get(f"/api/friends/{a['id']}")
    assert r.status_code == 200
    body = r.json()
    assert len(body["groups"]) == 1
    assert body["groups"][0]["id"] == g["id"]
    assert body["groups"][0]["name"] == "RPG"
    assert body["groups"][0]["color"] == "#f59e0b"


async def test_friends_list_filtro_group_id(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    b = await _create_friend(client, "Bruno")
    c = await _create_friend(client, "Carla")
    # So Ana e Bruno no grupo
    for fid in (a["id"], b["id"]):
        await client.post(
            f"/api/groups/{g['id']}/members", json={"friend_id": fid}
        )

    r = await client.get(f"/api/friends?group_id={g['id']}")
    assert r.status_code == 200
    names = [f["name"] for f in r.json()]
    assert names == ["Ana", "Bruno"]
    # Sanity: sem filtro aparece todo mundo
    r_all = await client.get("/api/friends")
    assert len(r_all.json()) == 3
    # Grupo inexistente = lista vazia (sem 404)
    r_empty = await client.get("/api/friends?group_id=9999")
    assert r_empty.status_code == 200
    assert r_empty.json() == []
    _ = c  # usado so pra checar que nao foi filtrado


async def test_bulk_add_group_via_friends_endpoint(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    b = await _create_friend(client, "Bruno")

    r = await client.post(
        "/api/friends/bulk/groups/add",
        json={"ids": [a["id"], b["id"]], "group_id": g["id"]},
    )
    assert r.status_code == 200
    assert r.json()["affected"] == 2


async def test_bulk_remove_group_via_friends_endpoint(client):
    g = await _create_group(client, "RPG")
    a = await _create_friend(client, "Ana")
    await client.post(
        "/api/friends/bulk/groups/add",
        json={"ids": [a["id"]], "group_id": g["id"]},
    )
    r = await client.post(
        "/api/friends/bulk/groups/remove",
        json={"ids": [a["id"]], "group_id": g["id"]},
    )
    assert r.status_code == 200
    assert r.json()["affected"] == 1


# ── Merge + groups ──────────────────────────────────────────────


async def test_merge_une_grupos_dos_sources(client):
    g1 = await _create_group(client, "RPG")
    g2 = await _create_group(client, "Trabalho")
    g3 = await _create_group(client, "Familia")

    primary = await _create_friend(client, "Ana")
    src = await _create_friend(client, "Ana Duplicada")

    # Primary ja em RPG; source em Trabalho + Familia + RPG (colisao).
    await client.post(
        f"/api/groups/{g1['id']}/members", json={"friend_id": primary["id"]}
    )
    for gid in (g1["id"], g2["id"], g3["id"]):
        await client.post(
            f"/api/groups/{gid}/members", json={"friend_id": src["id"]}
        )

    r = await client.post(
        "/api/friends/bulk/merge",
        json={"primary_id": primary["id"], "source_ids": [src["id"]]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["merged"] == 1
    # Primary agora tem os 3 grupos, sem duplicar RPG
    names = sorted(g["name"] for g in body["friend"]["groups"])
    assert names == ["Familia", "RPG", "Trabalho"]

    # Os grupos continuam com 1 membro cada (o primary)
    for gid, expected in [(g1["id"], 1), (g2["id"], 1), (g3["id"], 1)]:
        r2 = await client.get(f"/api/groups/{gid}")
        assert r2.json()["member_count"] == expected
