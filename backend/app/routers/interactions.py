"""Router de interacoes (13.7).

Endpoints aninhados ao amigo: `/api/friends/{friend_id}/interactions`.
Manter aninhado torna obvio o escopo (toda interacao pertence a um amigo)
e permite listar/criar sem paginar no nivel global.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.interaction import InteractionCreate, InteractionRead
from app.services import interaction_service

router = APIRouter(prefix="/api/friends/{friend_id}/interactions", tags=["interactions"])


@router.get("", response_model=list[InteractionRead])
async def list_interactions(
    friend_id: int,
    session: AsyncSession = Depends(get_db),
) -> list[InteractionRead]:
    return await interaction_service.list_interactions(session, friend_id)


@router.post("", response_model=InteractionRead, status_code=status.HTTP_201_CREATED)
async def create_interaction(
    friend_id: int,
    payload: InteractionCreate,
    session: AsyncSession = Depends(get_db),
) -> InteractionRead:
    return await interaction_service.create_interaction(session, friend_id, payload)
