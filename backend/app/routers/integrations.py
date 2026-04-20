"""Routers de integracoes externas (PRD §9.6).

Por ora so Evernote via IFTTT (13.12). Google Calendar (13.13) entra
no mesmo router quando implementado.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.sync import SyncEventRead
from app.services import evernote_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


class EvernoteSyncPayload(BaseModel):
    """Body do endpoint de sync: identifica qual interacao appendar."""

    interaction_id: int = Field(..., gt=0)


@router.post(
    "/evernote/friends/{friend_id}/sync",
    response_model=SyncEventRead,
)
async def sync_evernote(
    friend_id: int,
    payload: EvernoteSyncPayload,
    session: AsyncSession = Depends(get_db),
) -> SyncEventRead:
    """Dispara um append no Evernote para a interacao informada.

    Retorna o `SyncEvent` resultante (tanto sucesso quanto, implicito
    pelo status 502, falha — o registro e consultavel via DB).
    """
    return await evernote_service.sync_interaction_to_evernote(
        session, friend_id, payload.interaction_id
    )
