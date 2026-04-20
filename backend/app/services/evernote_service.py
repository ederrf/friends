"""Servico de sincronizacao com Evernote via IFTTT (PRD §11).

Orquestra:
1. busca da interacao + amigo
2. decisao sobre incluir cabecalho de metadados (so no primeiro append)
3. formatacao do corpo (`value2`) conforme PRD §11
4. chamada ao `ifttt_client.trigger_webhook`
5. registro em `sync_event` (success ou failed) — falha *preserva* o log e
   re-propaga o erro para virar 502 no router

Convencao de titulo: `Friends: {nome}` (sem id, o IFTTT nao devolve o
id da nota; o append depende unicamente do titulo).

Requisito central (PRD §7.2, §11):
    "falhas de webhook devem gerar registro em sync_events"
    "falhas nao podem impedir gravacao local da interacao"

A gravacao local acontece antes deste servico ser chamado (o router
aceita o id de uma interacao ja persistida), entao aqui so garantimos
que o log de falha sobrevive mesmo que a sessao da request seja
rollbackada pelo handler de erros.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.errors import NotFoundError
from app.models.friend import Friend
from app.models.interaction import Interaction
from app.models.sync_event import (
    SyncAction,
    SyncEntityType,
    SyncEvent,
    SyncProvider,
    SyncStatus,
)
from app.schemas.sync import SyncEventRead
from app.services import ifttt_client


# ── Formatacao do corpo ──────────────────────────────────────────


def _format_local_dt(dt: datetime) -> str:
    """`YYYY-MM-DD HH:MM` no timezone configurado. Sem segundos."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(settings.timezone))
    return dt.astimezone(ZoneInfo(settings.timezone)).strftime("%Y-%m-%d %H:%M")


def _entry_line(interaction: Interaction) -> str:
    """Linha `[YYYY-MM-DD HH:MM] {tipo}\\n{nota}` conforme PRD §11."""
    header = (
        f"[{_format_local_dt(interaction.occurred_at)}] "
        f"{interaction.interaction_type.value}"
    )
    note = (interaction.note or "").strip()
    return f"{header}\n{note}" if note else header


def _metadata_block(friend: Friend) -> str:
    """Cabecalho enviado apenas na primeira interacao de um amigo."""
    phone = friend.phone or "—"
    birthday = friend.birthday.isoformat() if friend.birthday else "—"
    tags = ", ".join(sorted(t.tag for t in friend.tags)) or "—"
    return (
        f"Friends: {friend.name}\n"
        f"Telefone: {phone} | Aniversario: {birthday}\n"
        f"Categoria: {friend.category.value} | Cadencia: {friend.cadence.value}\n"
        f"Tags: {tags}"
    )


def build_note_title(friend: Friend) -> str:
    return f"Friends: {friend.name}"


def build_note_body(
    friend: Friend, interaction: Interaction, *, include_header: bool
) -> str:
    entry = _entry_line(interaction)
    if include_header:
        return f"{_metadata_block(friend)}\n\n---\n\n{entry}"
    return entry


# ── Busca de dados ───────────────────────────────────────────────


async def _get_friend_with_tags(session: AsyncSession, friend_id: int) -> Friend:
    stmt = (
        select(Friend).options(selectinload(Friend.tags)).where(Friend.id == friend_id)
    )
    friend = (await session.execute(stmt)).scalar_one_or_none()
    if friend is None:
        raise NotFoundError("friend", friend_id)
    return friend


async def _get_interaction(
    session: AsyncSession, interaction_id: int, friend_id: int
) -> Interaction:
    """Exige que a interacao pertenca ao amigo — evita cross-friend leaks."""
    stmt = select(Interaction).where(
        Interaction.id == interaction_id,
        Interaction.friend_id == friend_id,
    )
    inter = (await session.execute(stmt)).scalar_one_or_none()
    if inter is None:
        raise NotFoundError("interaction", interaction_id)
    return inter


async def _previous_successful_sync_count(
    session: AsyncSession, friend_id: int
) -> int:
    """Conta appends bem-sucedidos previos para este amigo.

    Se zero, e o primeiro append e incluimos o cabecalho de metadados.
    Consideramos apenas `SUCCESS` — uma tentativa `FAILED` anterior nao
    "consome" o cabecalho, porque a nota no Evernote ainda nao existe.
    """
    inter_ids = select(Interaction.id).where(Interaction.friend_id == friend_id)
    stmt = select(func.count(SyncEvent.id)).where(
        SyncEvent.provider == SyncProvider.IFTTT,
        SyncEvent.entity_type == SyncEntityType.INTERACTION,
        SyncEvent.action == SyncAction.APPEND,
        SyncEvent.status == SyncStatus.SUCCESS,
        SyncEvent.entity_id.in_(inter_ids),
    )
    return int((await session.execute(stmt)).scalar_one())


# ── Entrada publica ──────────────────────────────────────────────


async def sync_interaction_to_evernote(
    session: AsyncSession,
    friend_id: int,
    interaction_id: int,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> SyncEventRead:
    """Dispara o webhook IFTTT para appendar a interacao na nota do amigo.

    Em caso de falha, o `sync_event` com `FAILED` e persistido via
    `session.commit()` *antes* de re-propagar o erro, para que o
    rollback do handler global nao apague o log. Em sucesso, o commit
    fica a cargo da dependencia `get_db`.
    """
    friend = await _get_friend_with_tags(session, friend_id)
    interaction = await _get_interaction(session, interaction_id, friend_id)

    previous = await _previous_successful_sync_count(session, friend_id)
    include_header = previous == 0

    title = build_note_title(friend)
    body = build_note_body(friend, interaction, include_header=include_header)
    payload: dict[str, Any] = {
        "value1": title,
        "value2": body,
        "include_header": include_header,
    }

    try:
        await ifttt_client.trigger_webhook(
            value1=title,
            value2=body,
            client=http_client,
        )
    except Exception as exc:
        event = SyncEvent(
            provider=SyncProvider.IFTTT,
            entity_type=SyncEntityType.INTERACTION,
            entity_id=interaction_id,
            action=SyncAction.APPEND,
            status=SyncStatus.FAILED,
            payload_json=payload,
            error_message=str(exc),
        )
        session.add(event)
        # Persiste o log antes de propagar — caso contrario o handler
        # global de erros rollbacka a sessao e perdemos a evidencia.
        await session.commit()
        raise

    event = SyncEvent(
        provider=SyncProvider.IFTTT,
        entity_type=SyncEntityType.INTERACTION,
        entity_id=interaction_id,
        action=SyncAction.APPEND,
        status=SyncStatus.SUCCESS,
        payload_json=payload,
    )
    session.add(event)
    await session.flush()
    return SyncEventRead.model_validate(event)


__all__ = [
    "build_note_body",
    "build_note_title",
    "sync_interaction_to_evernote",
]
