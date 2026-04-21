"""Servico de grupos (13.23).

Grupos sao entidades de primeira classe distintas de tags:
- nome unico (case-insensitive) + descricao + cor
- membership many-to-many com Friend via tabela friend_group
- operacoes: CRUD, add/remove membro, bulk add/remove

Convencoes seguidas:
- Ids duplicados em payload sao deduplicados silenciosamente (como bulk
  de tags).
- `not_found` silencioso em lote, 404 em rotas unitarias.
- Colisao de membership (amigo ja no grupo) entra em `skipped`, nao e
  erro — mesmo padrao usado em `bulk_add_tag`.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError, NotFoundError
from app.models.friend import Friend
from app.models.group import FriendGroup, Group
from app.schemas.friend import BulkOpResult
from app.schemas.group import GroupCreate, GroupRead, GroupUpdate


def _to_read(group: Group, member_count: int = 0) -> GroupRead:
    return GroupRead(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        member_count=member_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


# ── CRUD ─────────────────────────────────────────────────────────


async def list_groups(session: AsyncSession) -> list[GroupRead]:
    """Lista grupos ordenados por nome, com `member_count` agregado.

    LEFT JOIN + GROUP BY em 1 round-trip (alternativa seria N+1 com count
    por grupo).
    """
    stmt = (
        select(Group, func.count(FriendGroup.id))
        .outerjoin(FriendGroup, FriendGroup.group_id == Group.id)
        .group_by(Group.id)
        .order_by(func.lower(Group.name))
    )
    result = await session.execute(stmt)
    return [_to_read(g, count) for g, count in result.all()]


async def _get_group_orm(session: AsyncSession, group_id: int) -> Group:
    stmt = select(Group).where(Group.id == group_id)
    result = await session.execute(stmt)
    group = result.scalar_one_or_none()
    if group is None:
        raise NotFoundError("group", group_id)
    return group


async def _count_members(session: AsyncSession, group_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(FriendGroup)
        .where(FriendGroup.group_id == group_id)
    )
    return (await session.execute(stmt)).scalar_one()


async def get_group(session: AsyncSession, group_id: int) -> GroupRead:
    group = await _get_group_orm(session, group_id)
    return _to_read(group, await _count_members(session, group_id))


async def _ensure_unique_name(
    session: AsyncSession, name: str, *, exclude_id: int | None = None
) -> None:
    """Valida que `name` nao colide (case-insensitive) com grupo existente."""
    stmt = select(Group.id).where(func.lower(Group.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Group.id != exclude_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            "GROUP_NAME_TAKEN",
            f"Grupo '{name}' ja existe.",
            name=name,
        )


async def create_group(
    session: AsyncSession, payload: GroupCreate
) -> GroupRead:
    await _ensure_unique_name(session, payload.name)
    group = Group(
        name=payload.name,
        description=payload.description,
        color=payload.color,
    )
    session.add(group)
    await session.flush()
    return _to_read(group, 0)


async def update_group(
    session: AsyncSession, group_id: int, payload: GroupUpdate
) -> GroupRead:
    group = await _get_group_orm(session, group_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] and data["name"].lower() != group.name.lower():
        await _ensure_unique_name(session, data["name"], exclude_id=group_id)
    for field, value in data.items():
        setattr(group, field, value)
    await session.flush()
    # Re-fetch pra pegar o novo `updated_at` (server onupdate) sem disparar
    # lazy load no retorno. Consistente com friend_service.update_friend.
    return await get_group(session, group_id)


async def delete_group(session: AsyncSession, group_id: int) -> None:
    """Apaga grupo + todas as memberships (cascade)."""
    group = await _get_group_orm(session, group_id)
    # Iteramos ORM pra disparar cascade no FriendGroup (SQLite nao enforça
    # ondelete=CASCADE sem PRAGMA, replicando padrao do bulk_delete_friends).
    await session.delete(group)
    await session.flush()


# ── Membership ──────────────────────────────────────────────────


async def list_member_ids(
    session: AsyncSession, group_id: int
) -> list[int]:
    await _get_group_orm(session, group_id)  # 404 se nao existir
    stmt = select(FriendGroup.friend_id).where(
        FriendGroup.group_id == group_id
    )
    # Ordem estavel: por id crescente (frontend reordena por nome depois de hidratar).
    return sorted((await session.execute(stmt)).scalars().all())


async def add_member(
    session: AsyncSession, group_id: int, friend_id: int
) -> None:
    await _get_group_orm(session, group_id)
    exists_friend = await session.execute(
        select(Friend.id).where(Friend.id == friend_id)
    )
    if exists_friend.scalar_one_or_none() is None:
        raise NotFoundError("friend", friend_id)
    # Ja e membro? No-op silencioso (idempotente).
    existing = await session.execute(
        select(FriendGroup.id).where(
            FriendGroup.group_id == group_id,
            FriendGroup.friend_id == friend_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        return
    session.add(FriendGroup(group_id=group_id, friend_id=friend_id))
    await session.flush()


async def remove_member(
    session: AsyncSession, group_id: int, friend_id: int
) -> None:
    await _get_group_orm(session, group_id)
    result = await session.execute(
        delete(FriendGroup).where(
            FriendGroup.group_id == group_id,
            FriendGroup.friend_id == friend_id,
        )
    )
    if (result.rowcount or 0) == 0:
        raise NotFoundError("membership", f"{group_id}:{friend_id}")
    await session.flush()


# ── Bulk ────────────────────────────────────────────────────────


def _dedupe_preserving_order(ids: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


async def _existing_friend_ids(
    session: AsyncSession, ids: list[int]
) -> set[int]:
    if not ids:
        return set()
    result = await session.execute(
        select(Friend.id).where(Friend.id.in_(ids))
    )
    return set(result.scalars().all())


async def bulk_add_members(
    session: AsyncSession, group_id: int, friend_ids: list[int]
) -> BulkOpResult:
    """Adiciona varios amigos a um grupo. Ids ja-membros caem em `skipped`."""
    await _get_group_orm(session, group_id)
    unique_ids = _dedupe_preserving_order(friend_ids)
    existing = await _existing_friend_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in existing]

    if not existing:
        return BulkOpResult(affected=0, not_found=not_found)

    already_stmt = select(FriendGroup.friend_id).where(
        FriendGroup.group_id == group_id,
        FriendGroup.friend_id.in_(existing),
    )
    already = set((await session.execute(already_stmt)).scalars().all())
    to_add = [
        i for i in unique_ids if i in existing and i not in already
    ]
    for fid in to_add:
        session.add(FriendGroup(group_id=group_id, friend_id=fid))
    if to_add:
        await session.flush()

    return BulkOpResult(
        affected=len(to_add),
        not_found=not_found,
        skipped=sorted(already),
    )


async def bulk_remove_members(
    session: AsyncSession, group_id: int, friend_ids: list[int]
) -> BulkOpResult:
    """Remove varios amigos de um grupo. Ids que nao eram membros caem em `skipped`."""
    await _get_group_orm(session, group_id)
    unique_ids = _dedupe_preserving_order(friend_ids)
    existing = await _existing_friend_ids(session, unique_ids)
    not_found = [i for i in unique_ids if i not in existing]

    if not existing:
        return BulkOpResult(affected=0, not_found=not_found)

    had_stmt = select(FriendGroup.friend_id).where(
        FriendGroup.group_id == group_id,
        FriendGroup.friend_id.in_(existing),
    )
    had = set((await session.execute(had_stmt)).scalars().all())
    if had:
        await session.execute(
            delete(FriendGroup).where(
                FriendGroup.group_id == group_id,
                FriendGroup.friend_id.in_(had),
            )
        )
        await session.flush()

    skipped = sorted(i for i in existing if i not in had)
    return BulkOpResult(
        affected=len(had), not_found=not_found, skipped=skipped
    )
