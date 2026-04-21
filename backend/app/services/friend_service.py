"""Servico de CRUD de amigos.

Concentra o acesso ao DB e a hidratacao de `FriendRead` com metricas de
dominio calculadas em `services.friendship`.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import ConflictError, NotFoundError
from app.models.calendar_link import CalendarLink
from app.models.friend import Cadence, Category, Friend
from app.models.friend_tag import FriendTag
from app.models.group import FriendGroup
from app.models.interaction import Interaction
from app.schemas.friend import (
    BulkOpResult,
    FriendCreate,
    FriendRead,
    FriendUpdate,
    MergeResult,
)
from app.schemas.group import GroupRef
from app.services.friendship import compute_friend_metrics


def _normalize_tag(tag: str) -> str:
    """Tags sao normalizadas para lowercase e sem espacos nas pontas."""
    return tag.strip().lower()


def _unique_tags(tags: list[str]) -> list[str]:
    """Remove duplicatas preservando ordem, apos normalizacao."""
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        norm = _normalize_tag(t)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def to_read(friend: Friend) -> FriendRead:
    """Converte ORM Friend em FriendRead com metricas, tags e grupos.

    Requer que `friend.tags` e `friend.groups` (+ `FriendGroup.group`)
    ja tenham sido carregados via selectinload. Relacao lazy nao e aceita
    em contexto async.
    """
    metrics = compute_friend_metrics(
        friend.cadence, friend.last_contact_at, friend.created_at
    )
    group_refs = sorted(
        (GroupRef.model_validate(fg.group) for fg in friend.groups),
        key=lambda g: g.name.lower(),
    )
    return FriendRead(
        id=friend.id,
        name=friend.name,
        phone=friend.phone,
        email=friend.email,
        birthday=friend.birthday,
        category=friend.category,
        cadence=friend.cadence,
        notes=friend.notes,
        last_contact_at=friend.last_contact_at,
        created_at=friend.created_at,
        updated_at=friend.updated_at,
        tags=sorted(t.tag for t in friend.tags),
        groups=group_refs,
        days_since_last_contact=metrics.days_since_last_contact,
        days_until_next_ping=metrics.days_until_next_ping,
        temperature=metrics.temperature,
        temperature_label=metrics.temperature_label,
    )


def _friend_loaders():
    """selectinload padronizado: tags + groups (com Group ref)."""
    return [
        selectinload(Friend.tags),
        selectinload(Friend.groups).selectinload(FriendGroup.group),
    ]


async def list_friends(
    session: AsyncSession,
    *,
    category: Category | None = None,
    cadence: Cadence | None = None,
    tag: str | None = None,
    group_id: int | None = None,
    no_group: bool = False,
) -> list[FriendRead]:
    """Lista amigos com filtros opcionais.

    `group_id`: restringe a amigos que sao membros do grupo. Grupo
    inexistente devolve lista vazia (nao 404) — coerente com o filtro
    de tag (string livre que pode nao casar com nada).

    `no_group`: restringe a amigos que NAO pertencem a nenhum grupo —
    util pra encontrar quem ainda nao foi agrupado. Mutuamente exclusivo
    com `group_id` (o router valida e rejeita o combo).
    """
    stmt = select(Friend).options(*_friend_loaders())
    if category is not None:
        stmt = stmt.where(Friend.category == category)
    if cadence is not None:
        stmt = stmt.where(Friend.cadence == cadence)
    if tag is not None:
        tag_norm = _normalize_tag(tag)
        stmt = stmt.join(Friend.tags).where(FriendTag.tag == tag_norm)
    if group_id is not None:
        stmt = stmt.join(FriendGroup, FriendGroup.friend_id == Friend.id).where(
            FriendGroup.group_id == group_id
        )
    elif no_group:
        # NOT EXISTS e mais claro que outer-join + IS NULL e funciona bem
        # em SQLite/Postgres sem truques de DISTINCT.
        subq = select(FriendGroup.friend_id).where(
            FriendGroup.friend_id == Friend.id
        )
        stmt = stmt.where(~subq.exists())
    stmt = stmt.order_by(Friend.name)

    result = await session.execute(stmt)
    friends = result.scalars().unique().all()
    return [to_read(f) for f in friends]


async def list_friends_by_ids(
    session: AsyncSession, friend_ids: list[int]
) -> list[FriendRead]:
    """Hidrata FriendRead para um conjunto de ids, ordenado por nome.

    Usado por endpoints como `GET /api/groups/{id}/members` que ja
    calcularam o filtro antes. Ids inexistentes sao ignorados.
    """
    if not friend_ids:
        return []
    stmt = (
        select(Friend)
        .options(*_friend_loaders())
        .where(Friend.id.in_(friend_ids))
        .order_by(Friend.name)
    )
    result = await session.execute(stmt)
    return [to_read(f) for f in result.scalars().unique().all()]


async def _get_friend_orm(session: AsyncSession, friend_id: int) -> Friend:
    stmt = (
        select(Friend)
        .options(*_friend_loaders())
        .where(Friend.id == friend_id)
    )
    result = await session.execute(stmt)
    friend = result.scalar_one_or_none()
    if friend is None:
        raise NotFoundError("friend", friend_id)
    return friend


async def get_friend(session: AsyncSession, friend_id: int) -> FriendRead:
    friend = await _get_friend_orm(session, friend_id)
    return to_read(friend)


async def create_friend(session: AsyncSession, payload: FriendCreate) -> FriendRead:
    friend = Friend(
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
        birthday=payload.birthday,
        category=payload.category,
        cadence=payload.cadence,
        notes=payload.notes,
    )
    session.add(friend)
    await session.flush()

    for tag in _unique_tags(payload.tags):
        session.add(FriendTag(friend_id=friend.id, tag=tag))

    await session.flush()
    # Re-seleciona com selectinload para garantir que tags estao carregadas
    # e evitar lazy load em contexto async.
    return await get_friend(session, friend.id)


async def update_friend(
    session: AsyncSession, friend_id: int, payload: FriendUpdate
) -> FriendRead:
    friend = await _get_friend_orm(session, friend_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(friend, field, value)
    await session.flush()
    return await get_friend(session, friend.id)


async def delete_friend(session: AsyncSession, friend_id: int) -> None:
    friend = await _get_friend_orm(session, friend_id)
    await session.delete(friend)
    await session.flush()


# ── Bulk actions ─────────────────────────────────────────────────
#
# Estrategia comum:
#   1. descobre quais ids existem (uma unica query)
#   2. calcula `not_found` antes de mutar
#   3. aplica a acao via UPDATE/DELETE em massa (sem ORM por item)
#   4. devolve BulkOpResult uniforme
#
# Ids duplicados no payload sao deduplicados; a ordem de `not_found`
# preserva a do request pra facilitar debug no frontend.


def _dedupe_preserving_order(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


async def _existing_ids(session: AsyncSession, ids: list[int]) -> set[int]:
    if not ids:
        return set()
    result = await session.execute(select(Friend.id).where(Friend.id.in_(ids)))
    return set(result.scalars().all())


async def bulk_delete_friends(
    session: AsyncSession, ids: list[int]
) -> BulkOpResult:
    """Apaga em lote. Cascata de tags/interactions e garantida pelo modelo."""
    unique_ids = _dedupe_preserving_order(ids)
    found = await _existing_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in found]

    if found:
        # Iteramos via ORM pra acionar cascade delete configurado no modelo
        # (FriendTag / Interaction). DELETE IN() direto pularia isso no SQLite.
        for friend in (
            (await session.execute(select(Friend).where(Friend.id.in_(found))))
            .scalars()
            .all()
        ):
            await session.delete(friend)
        await session.flush()

    return BulkOpResult(affected=len(found), not_found=not_found)


async def bulk_touch_friends(
    session: AsyncSession, ids: list[int]
) -> BulkOpResult:
    """Marca `last_contact_at = agora` em lote.

    Util depois de um import massivo: neutraliza a temperatura dos
    contatos sem criar Interaction — e acao de limpeza, nao registro
    de interacao real. Se quiser um `Interaction` de verdade, use o
    endpoint individual de interacoes.

    `last_contact_at` so avanca (coerente com a regra do
    interaction_service): se algum amigo ja tiver contato mais recente,
    o touch ainda assim sobrescreve — e acao explicita do usuario,
    entao aqui nao fazemos o `max()` que faz sentido na rota de
    interacao historica.
    """
    unique_ids = _dedupe_preserving_order(ids)
    found = await _existing_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in found]

    if found:
        now = datetime.now(ZoneInfo(settings.timezone))
        await session.execute(
            update(Friend).where(Friend.id.in_(found)).values(last_contact_at=now)
        )
        await session.flush()

    return BulkOpResult(affected=len(found), not_found=not_found)


async def bulk_add_tag(
    session: AsyncSession, ids: list[int], raw_tag: str
) -> BulkOpResult:
    """Aplica a mesma tag a varios amigos.

    - normaliza a tag (lower + strip); tag vazia => 409 TAG_INVALID.
    - amigos que ja possuem a tag entram em `skipped` (nao e erro).
    - ids inexistentes entram em `not_found`.
    """
    tag = _normalize_tag(raw_tag)
    if not tag:
        raise ConflictError(
            "TAG_INVALID", "Tag vazia apos normalizacao.", tag=raw_tag
        )

    unique_ids = _dedupe_preserving_order(ids)
    found = await _existing_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in found]

    if not found:
        return BulkOpResult(affected=0, not_found=not_found)

    already_stmt = select(FriendTag.friend_id).where(
        FriendTag.friend_id.in_(found), FriendTag.tag == tag
    )
    already_set = set((await session.execute(already_stmt)).scalars().all())
    to_add = [i for i in unique_ids if i in found and i not in already_set]

    for fid in to_add:
        session.add(FriendTag(friend_id=fid, tag=tag))
    if to_add:
        await session.flush()

    return BulkOpResult(
        affected=len(to_add),
        not_found=not_found,
        skipped=sorted(already_set),
    )


async def bulk_remove_tag(
    session: AsyncSession, ids: list[int], raw_tag: str
) -> BulkOpResult:
    """Remove a tag de varios amigos.

    Ids sem a tag entram em `skipped`. Diferente do endpoint individual
    (que devolve 404 pra tag ausente), em lote ausencia nao e erro —
    o usuario esta limpando e nao e obrigado a saber quem tinha o que.
    """
    tag = _normalize_tag(raw_tag)
    if not tag:
        raise ConflictError(
            "TAG_INVALID", "Tag vazia apos normalizacao.", tag=raw_tag
        )

    unique_ids = _dedupe_preserving_order(ids)
    found = await _existing_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in found]

    if not found:
        return BulkOpResult(affected=0, not_found=not_found)

    had_stmt = select(FriendTag.friend_id).where(
        FriendTag.friend_id.in_(found), FriendTag.tag == tag
    )
    had_set = set((await session.execute(had_stmt)).scalars().all())

    if had_set:
        await session.execute(
            delete(FriendTag).where(
                FriendTag.friend_id.in_(had_set), FriendTag.tag == tag
            )
        )
        await session.flush()

    skipped = sorted(i for i in found if i not in had_set)
    return BulkOpResult(affected=len(had_set), not_found=not_found, skipped=skipped)


# ── Merge ────────────────────────────────────────────────────────
#
# Uso tipico pos-import: CSV/VCF trouxe duplicatas do mesmo contato.
# O usuario seleciona os duplicados, escolhe o "canonico" (primary) e
# os demais sao fundidos nele:
#   - Interactions: FK migra pro primary (preserva historico).
#   - Tags: uniao deduplicada. FriendTag tem unique (friend_id, tag);
#     colisao resolve deletando a do source em vez de mover.
#   - CalendarLink: primary mantem o seu; sources sao descartados
#     (unique (friend_id, provider) impediria move).
#   - last_contact_at: max entre todos (coerente com interaction_service).
#   - Campos escalares vazios do primary (phone/email/birthday/notes)
#     sao preenchidos com o primeiro nao-vazio dos sources, na ordem
#     recebida. Nome/category/cadence sao escolhas do usuario, nunca
#     sobrescritas.
#   - Sources sao deletados ao final (cascade limpa residuos: se um
#     FriendTag ficou no source por ja existir no primary, ele vai
#     embora com o source).
#
# SyncEvent aponta pra Interaction.id, nao friend_id — acompanha a
# interaction movida automaticamente, sem intervencao.


_FILLABLE_SCALARS = ("phone", "email", "birthday", "notes")


def _fill_empty_from_sources(primary: Friend, sources: list[Friend]) -> None:
    """Preenche campos escalares vazios do primary com o 1o nao-vazio dos sources."""
    for field in _FILLABLE_SCALARS:
        if getattr(primary, field):
            continue
        for src in sources:
            val = getattr(src, field)
            if val:
                setattr(primary, field, val)
                break


async def merge_friends(
    session: AsyncSession,
    primary_id: int,
    source_ids: list[int],
) -> MergeResult:
    """Funde sources no primary.

    - primary_id inexistente -> 404.
    - source_ids duplicados e a presenca do primary_id em source_ids
      sao filtrados silenciosamente (ids patologicos no payload nao
      devem virar erro).
    - sources inexistentes entram em `not_found`.
    - Se sobrarem 0 sources validos, retorna o primary sem mudanca
      e `merged=0`.
    """
    primary = await _get_friend_orm(session, primary_id)  # 404 aqui

    # Dedup + remove o primary de dentro da lista de sources
    unique_sources = [
        i for i in _dedupe_preserving_order(source_ids) if i != primary_id
    ]
    found = await _existing_ids(session, unique_sources)
    not_found = [i for i in unique_sources if i not in found]
    valid_source_ids = [i for i in unique_sources if i in found]

    if not valid_source_ids:
        return MergeResult(
            friend=to_read(primary),
            merged=0,
            not_found=not_found,
            interactions_moved=0,
            tags_added=0,
        )

    # Carrega sources com tags, groups e last_contact_at pra usar nos merges
    sources_stmt = (
        select(Friend)
        .options(*_friend_loaders())
        .where(Friend.id.in_(valid_source_ids))
    )
    # Preserva a ordem pedida (importante pra "primeiro nao-vazio")
    sources_by_id = {
        s.id: s for s in (await session.execute(sources_stmt)).scalars().all()
    }
    sources = [sources_by_id[i] for i in valid_source_ids]

    # ── Interactions: FK move pro primary em massa ──
    interactions_result = await session.execute(
        update(Interaction)
        .where(Interaction.friend_id.in_(valid_source_ids))
        .values(friend_id=primary_id)
    )
    interactions_moved = interactions_result.rowcount or 0

    # ── Tags: move as novas, deleta as colisoes ──
    #
    # Reatribuimos via `ft.friend = primary` (lado many-to-one da relacao)
    # em vez de `ft.friend_id = primary_id`. O primeiro caminho mantem
    # `src.tags` e `primary.tags` sincronizados no cache do ORM — senao
    # a cascade do `delete-orphan` em `session.delete(src)` mais abaixo
    # acabaria apagando as tags recem-movidas.
    primary_tags = {t.tag for t in primary.tags}
    tags_added = 0
    for src in sources:
        for ft in list(src.tags):
            if ft.tag in primary_tags:
                # Colisao: source tem tag que o primary ja tem. Remover
                # da colecao do source dispara delete-orphan e apaga.
                src.tags.remove(ft)
            else:
                ft.friend = primary
                primary_tags.add(ft.tag)
                tags_added += 1

    # ── Groups: mesma logica das tags (uniao com dedup) ──
    primary_group_ids = {fg.group_id for fg in primary.groups}
    for src in sources:
        for fg in list(src.groups):
            if fg.group_id in primary_group_ids:
                src.groups.remove(fg)
            else:
                fg.friend = primary
                primary_group_ids.add(fg.group_id)

    # ── CalendarLink: primary mantem; sources sao descartados ──
    # Delete explicito antes do source.delete() pra evitar surpresa com
    # cascade + unique constraint caso alguem mude o modelo.
    await session.execute(
        delete(CalendarLink).where(CalendarLink.friend_id.in_(valid_source_ids))
    )

    # ── last_contact_at: max entre todos ──
    candidates = [primary.last_contact_at] + [s.last_contact_at for s in sources]
    non_null = [c for c in candidates if c is not None]
    if non_null:
        primary.last_contact_at = max(non_null)

    # ── Preenche campos escalares vazios do primary ──
    _fill_empty_from_sources(primary, sources)

    await session.flush()

    # ── Delete sources ──
    for src in sources:
        await session.delete(src)
    await session.flush()

    # Re-carrega o primary com tags atualizadas pra hidratacao correta
    return MergeResult(
        friend=await get_friend(session, primary_id),
        merged=len(valid_source_ids),
        not_found=not_found,
        interactions_moved=interactions_moved,
        tags_added=tags_added,
    )
