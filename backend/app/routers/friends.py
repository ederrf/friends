"""Router de amigos (13.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.friend import Cadence, Category
from app.schemas.friend import FriendCreate, FriendRead, FriendUpdate
from app.services import friend_service

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.get("", response_model=list[FriendRead])
async def list_friends(
    category: Category | None = Query(default=None),
    cadence: Cadence | None = Query(default=None),
    tag: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[FriendRead]:
    return await friend_service.list_friends(
        session, category=category, cadence=cadence, tag=tag
    )


@router.post("", response_model=FriendRead, status_code=status.HTTP_201_CREATED)
async def create_friend(
    payload: FriendCreate,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await friend_service.create_friend(session, payload)


@router.get("/{friend_id}", response_model=FriendRead)
async def get_friend(
    friend_id: int,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await friend_service.get_friend(session, friend_id)


@router.patch("/{friend_id}", response_model=FriendRead)
async def update_friend(
    friend_id: int,
    payload: FriendUpdate,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await friend_service.update_friend(session, friend_id, payload)


@router.delete("/{friend_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_friend(
    friend_id: int,
    session: AsyncSession = Depends(get_db),
) -> None:
    await friend_service.delete_friend(session, friend_id)
