"""Router de amigos (13.6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import AppError
from app.models.friend import Cadence, Category
from app.schemas.friend import (
    BulkIdsPayload,
    BulkOpResult,
    BulkTagPayload,
    FriendCreate,
    FriendRead,
    FriendUpdate,
    MergePayload,
    MergeResult,
)
from app.schemas.group import BulkGroupPayload
from app.services import friend_service, group_service

router = APIRouter(prefix="/api/friends", tags=["friends"])


@router.get("", response_model=list[FriendRead])
async def list_friends(
    category: Category | None = Query(default=None),
    cadence: Cadence | None = Query(default=None),
    tag: str | None = Query(default=None),
    group_id: int | None = Query(default=None, ge=1),
    no_group: bool = Query(default=False),
    session: AsyncSession = Depends(get_db),
) -> list[FriendRead]:
    if no_group and group_id is not None:
        # Combo sem sentido: "sem grupo" + "no grupo X". Rejeita cedo
        # pra o frontend nao mandar filtro contraditorio e achar que
        # o backend esta bugado devolvendo lista vazia.
        raise AppError(
            code="FILTER_CONFLICT",
            message="no_group e group_id sao mutuamente exclusivos.",
            status_code=400,
        )
    return await friend_service.list_friends(
        session,
        category=category,
        cadence=cadence,
        tag=tag,
        group_id=group_id,
        no_group=no_group,
    )


@router.post("", response_model=FriendRead, status_code=status.HTTP_201_CREATED)
async def create_friend(
    payload: FriendCreate,
    session: AsyncSession = Depends(get_db),
) -> FriendRead:
    return await friend_service.create_friend(session, payload)


# ── Bulk actions ─────────────────────────────────────────────────
#
# Prefixo `/bulk` evita colisao com `/{friend_id}` (path param int).
# Todos devolvem `BulkOpResult` pra UI montar toast uniforme.


@router.post("/bulk/delete", response_model=BulkOpResult)
async def bulk_delete_friends(
    payload: BulkIdsPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    return await friend_service.bulk_delete_friends(session, payload.ids)


@router.post("/bulk/touch", response_model=BulkOpResult)
async def bulk_touch_friends(
    payload: BulkIdsPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    """Marca os amigos como contatados agora (temperatura -> 100)."""
    return await friend_service.bulk_touch_friends(session, payload.ids)


@router.post("/bulk/tags/add", response_model=BulkOpResult)
async def bulk_add_tag(
    payload: BulkTagPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    return await friend_service.bulk_add_tag(session, payload.ids, payload.tag)


@router.post("/bulk/tags/remove", response_model=BulkOpResult)
async def bulk_remove_tag(
    payload: BulkTagPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    return await friend_service.bulk_remove_tag(session, payload.ids, payload.tag)


@router.post("/bulk/merge", response_model=MergeResult)
async def merge_friends(
    payload: MergePayload,
    session: AsyncSession = Depends(get_db),
) -> MergeResult:
    """Funde varios amigos (sources) em um primario.

    Uso tipico: limpar duplicatas criadas por imports. Interactions dos
    sources migram pro primary, tags e grupos sao unificados, sources
    sao deletados. Veja `friend_service.merge_friends` para detalhes.
    """
    return await friend_service.merge_friends(
        session, payload.primary_id, payload.source_ids
    )


@router.post("/bulk/groups/add", response_model=BulkOpResult)
async def bulk_add_group(
    payload: BulkGroupPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    """Adiciona varios amigos a um grupo de uma vez.

    Reusa `group_service.bulk_add_members` — grupo inexistente vira 404,
    ids inexistentes entram em `not_found`, ja-membros em `skipped`.
    """
    return await group_service.bulk_add_members(
        session, payload.group_id, payload.ids
    )


@router.post("/bulk/groups/remove", response_model=BulkOpResult)
async def bulk_remove_group(
    payload: BulkGroupPayload,
    session: AsyncSession = Depends(get_db),
) -> BulkOpResult:
    """Remove varios amigos de um grupo de uma vez."""
    return await group_service.bulk_remove_members(
        session, payload.group_id, payload.ids
    )


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
