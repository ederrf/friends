"""Servico de tags / interesses.

Centraliza:
- listagem global de interesses com contagem (`GET /api/interests`)
- adicao e remocao de tag individual de um amigo

Normalizacao reutilizada de `friend_service._normalize_tag` para manter
consistencia com o caminho de criacao/update de amigo.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.friend import Friend
from app.models.friend_tag import FriendTag
from app.schemas.friend import FriendRead
from app.schemas.tag import InterestSummary
from app.services.friend_service import _normalize_tag, get_friend


async def _ensure_friend_exists(session: AsyncSession, friend_id: int) -> None:
    friend = await session.get(Friend, friend_id)
    if friend is None:
        raise NotFoundError("friend", friend_id)


async def list_interests(session: AsyncSession) -> list[InterestSummary]:
    """Todas as tags com contagem de amigos, ordenadas por contagem DESC.

    Inclui tags com 1 amigo (diferente de `dashboard/clusters`, que filtra
    por `min_cluster_size=2`). Tags "solo" aqui viram `unique_interests`
    na camada de interesse.
    """
    stmt = (
        select(FriendTag.tag, func.count(FriendTag.friend_id.distinct()).label("c"))
        .group_by(FriendTag.tag)
        .order_by(func.count(FriendTag.friend_id.distinct()).desc(), FriendTag.tag)
    )
    result = await session.execute(stmt)
    return [InterestSummary(tag=tag, friend_count=count) for tag, count in result.all()]


async def add_tag_to_friend(
    session: AsyncSession, friend_id: int, raw_tag: str
) -> FriendRead:
    """Adiciona uma tag a um amigo.

    Regras:
    - normaliza a tag (lower + strip); rejeita vazia
    - tag ja presente -> 409 TAG_ALREADY_EXISTS (unique constraint
      `uq_friend_tag_friend_tag` garante no banco; checamos antes para
      devolver erro limpo em vez de IntegrityError)
    - retorna o `FriendRead` completo atualizado (a UI pode reusar)
    """
    await _ensure_friend_exists(session, friend_id)
    tag = _normalize_tag(raw_tag)
    if not tag:
        raise ConflictError("TAG_INVALID", "Tag vazia apos normalizacao.", tag=raw_tag)

    existing = await session.execute(
        select(FriendTag).where(
            FriendTag.friend_id == friend_id, FriendTag.tag == tag
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(
            "TAG_ALREADY_EXISTS",
            f"Amigo {friend_id} ja possui a tag '{tag}'.",
            friend_id=friend_id,
            tag=tag,
        )

    session.add(FriendTag(friend_id=friend_id, tag=tag))
    await session.flush()
    return await get_friend(session, friend_id)


async def remove_tag_from_friend(
    session: AsyncSession, friend_id: int, raw_tag: str
) -> FriendRead:
    """Remove uma tag de um amigo.

    - normaliza a tag antes de deletar
    - tag ausente no amigo -> 404 TAG_NOT_FOUND (evita silencio ao
      clicar duas vezes no mesmo botao por engano)
    """
    await _ensure_friend_exists(session, friend_id)
    tag = _normalize_tag(raw_tag)

    result = await session.execute(
        delete(FriendTag).where(
            FriendTag.friend_id == friend_id, FriendTag.tag == tag
        )
    )
    if result.rowcount == 0:
        raise NotFoundError("tag", f"{friend_id}:{tag}")

    await session.flush()
    return await get_friend(session, friend_id)
