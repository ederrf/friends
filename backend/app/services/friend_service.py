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
from app.models.friend import Cadence, Category, Friend
from app.models.friend_tag import FriendTag
from app.schemas.friend import BulkOpResult, FriendCreate, FriendRead, FriendUpdate
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
    """Converte ORM Friend em FriendRead com metricas e tags hidratadas.

    Requer que `friend.tags` ja tenha sido carregado (selectinload ou
    equivalente). Relacao lazy nao e aceita em contexto async.
    """
    metrics = compute_friend_metrics(
        friend.cadence, friend.last_contact_at, friend.created_at
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
        days_since_last_contact=metrics.days_since_last_contact,
        days_until_next_ping=metrics.days_until_next_ping,
        temperature=metrics.temperature,
        temperature_label=metrics.temperature_label,
    )


async def list_friends(
    session: AsyncSession,
    *,
    category: Category | None = None,
    cadence: Cadence | None = None,
    tag: str | None = None,
) -> list[FriendRead]:
    """Lista amigos com filtros opcionais."""
    stmt = select(Friend).options(selectinload(Friend.tags))
    if category is not None:
        stmt = stmt.where(Friend.category == category)
    if cadence is not None:
        stmt = stmt.where(Friend.cadence == cadence)
    if tag is not None:
        tag_norm = _normalize_tag(tag)
        stmt = stmt.join(Friend.tags).where(FriendTag.tag == tag_norm)
    stmt = stmt.order_by(Friend.name)

    result = await session.execute(stmt)
    friends = result.scalars().unique().all()
    return [to_read(f) for f in friends]


async def _get_friend_orm(session: AsyncSession, friend_id: int) -> Friend:
    stmt = select(Friend).options(selectinload(Friend.tags)).where(Friend.id == friend_id)
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
