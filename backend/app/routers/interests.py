"""Router de interesses e tags (13.9).

`GET /api/interests` lista agregada (todas as tags + contagem).
`POST/DELETE /api/friends/{id}/tags` atua na tag individual de um amigo.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.friend import FriendRead
from app.schemas.tag import InterestSummary, TagCreate
from app.services import tag_service

# ── /api/interests ──────────────────────────────────────────────
interests_router = APIRouter(prefix="/api/interests", tags=["interests"])


@interests_router.get("", response_model=list[InterestSummary])
async def list_interests(
    session: AsyncSession = Depends(get_db),
) -> list[InterestSummary]:
    return await tag_service.list_interests(session)


# ── /api/friends/{friend_id}/tags ───────────────────────────────
tags_router = APIRouter(
    prefix="/api/friends/{friend_id}/tags", tags=["tags"]
)


@tags_router.post("", response_model=FriendRead, status_code=status.HTTP_201_CREATED)
async def add_tag(
    friend_id: int,
    payload: TagCreate,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await tag_service.add_tag_to_friend(session, friend_id, payload.tag)


@tags_router.delete("/{tag}", response_model=FriendRead)
async def remove_tag(
    friend_id: int,
    tag: str,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await tag_service.remove_tag_from_friend(session, friend_id, tag)
