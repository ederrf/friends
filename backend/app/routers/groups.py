"""Router de grupos (13.23).

Expoe CRUD de `Group` + membership (add/remove/bulk) + listagem
hidratada dos membros.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.friend import BulkOpResult, FriendRead
from app.schemas.group import (
    BulkFriendIdsPayload,
    GroupCreate,
    GroupMembership,
    GroupRead,
    GroupUpdate,
)
from app.services import friend_service, group_service

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.get("", response_model=list[GroupRead])
async def list_groups(
    session: AsyncSession = Depends(get_db),
) -> list[GroupRead]:
    return await group_service.list_groups(session)


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    session: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await group_service.create_group(session, payload)


@router.get("/{group_id}", response_model=GroupRead)
async def get_group(
    group_id: int,
    session: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await group_service.get_group(session, group_id)


@router.patch("/{group_id}", response_model=GroupRead)
async def update_group(
    group_id: int,
    payload: GroupUpdate,
    session: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await group_service.update_group(session, group_id, payload)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    await group_service.delete_group(session, group_id)


# ── Membership ──────────────────────────────────────────────────


@router.get("/{group_id}/members", response_model=list[FriendRead])
async def list_members(
    group_id: int,
    session: AsyncSession = Depends(get_db),
) -> list[FriendRead]:
    """Lista os amigos do grupo hidratados (FriendRead completo).

    Delega a leitura de ids ao group_service e a hidratacao ao
    friend_service — evita duplicar a logica de metricas/temperatura.
    """
    friend_ids = await group_service.list_member_ids(session, group_id)
    return await friend_service.list_friends_by_ids(session, friend_ids)


@router.post("/{group_id}/members", status_code=status.HTTP_204_NO_CONTENT)
async def add_member(
    group_id: int,
    payload: GroupMembership,
    session: AsyncSession = Depends(get_db),
) -> None:
    await group_service.add_member(session, group_id, payload.friend_id)


@router.delete(
    "/{group_id}/members/{friend_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    group_id: int,
    friend_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    await group_service.remove_member(session, group_id, friend_id)


# ── Bulk membership ─────────────────────────────────────────────


@router.post("/{group_id}/members/bulk/add", response_model=BulkOpResult)
async def bulk_add(
    group_id: int,
    payload: BulkFriendIdsPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    return await group_service.bulk_add_members(
        session, group_id, payload.friend_ids
    )


@router.post("/{group_id}/members/bulk/remove", response_model=BulkOpResult)
async def bulk_remove(
    group_id: int,
    payload: BulkFriendIdsPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    return await group_service.bulk_remove_members(
        session, group_id, payload.friend_ids
    )
