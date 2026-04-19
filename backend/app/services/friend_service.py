"""Servico de CRUD de amigos.

Concentra o acesso ao DB e a hidratacao de `FriendRead` com metricas de
dominio calculadas em `services.friendship`.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import NotFoundError
from app.models.friend import Cadence, Category, Friend
from app.models.friend_tag import FriendTag
from app.schemas.friend import FriendCreate, FriendRead, FriendUpdate
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
