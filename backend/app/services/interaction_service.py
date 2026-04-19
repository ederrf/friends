"""Servico de interacoes.

Registra e lista interacoes por amigo. Ao registrar, atualiza
`friend.last_contact_at` para o maximo entre o valor atual e o
`occurred_at` da nova interacao — assim, uma interacao historica
(registrada com `occurred_at` no passado) nao rebaixa o contato mais
recente ja conhecido.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.errors import NotFoundError
from app.models.friend import Friend
from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate, InteractionRead


def _now_tz() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def _aware(dt: datetime) -> datetime:
    """Garante datetime com timezone; naive vira tz do app."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ZoneInfo(settings.timezone))
    return dt


async def _get_friend(session: AsyncSession, friend_id: int) -> Friend:
    friend = await session.get(Friend, friend_id)
    if friend is None:
        raise NotFoundError("friend", friend_id)
    return friend


async def list_interactions(
    session: AsyncSession, friend_id: int
) -> list[InteractionRead]:
    """Lista interacoes de um amigo ordenadas da mais recente para a mais antiga."""
    await _get_friend(session, friend_id)  # valida existencia (404 correto)
    stmt = (
        select(Interaction)
        .where(Interaction.friend_id == friend_id)
        .order_by(Interaction.occurred_at.desc(), Interaction.id.desc())
    )
    result = await session.execute(stmt)
    return [InteractionRead.model_validate(i) for i in result.scalars().all()]


async def create_interaction(
    session: AsyncSession, friend_id: int, payload: InteractionCreate
) -> InteractionRead:
    """Registra uma interacao e atualiza `last_contact_at` do amigo.

    Regra: `friend.last_contact_at` so avanca — uma interacao historica
    nao sobrescreve um contato mais recente.
    """
    friend = await _get_friend(session, friend_id)
    occurred_at = payload.occurred_at or _now_tz()
    occurred_at = _aware(occurred_at)

    interaction = Interaction(
        friend_id=friend_id,
        occurred_at=occurred_at,
        note=payload.note,
        interaction_type=payload.interaction_type,
    )
    session.add(interaction)

    current_last = friend.last_contact_at
    if current_last is None or _aware(current_last) < occurred_at:
        friend.last_contact_at = occurred_at

    await session.flush()
    return InteractionRead.model_validate(interaction)
