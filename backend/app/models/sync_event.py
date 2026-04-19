"""Sync event log model.

Registra toda tentativa de sincronizacao com provedores externos (IFTTT,
Google Calendar). Falhas ficam persistidas sem impedir gravacao local da
interacao que as originou.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SyncProvider(StrEnum):
    """Provedor externo alvo da sincronizacao."""

    IFTTT = "ifttt"
    GOOGLE_CALENDAR = "google_calendar"


class SyncEntityType(StrEnum):
    """Tipo da entidade local que originou o evento de sync."""

    FRIEND = "friend"
    INTERACTION = "interaction"
    CALENDAR_LINK = "calendar_link"


class SyncAction(StrEnum):
    """Acao executada (ou tentada) no provedor externo."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPEND = "append"


class SyncStatus(StrEnum):
    """Resultado da tentativa de sincronizacao."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class SyncEvent(Base):
    """Log de uma tentativa de sincronizacao com um provedor externo."""

    __tablename__ = "sync_event"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    provider: Mapped[SyncProvider] = mapped_column(
        SAEnum(SyncProvider, values_callable=lambda e: [m.value for m in e]),
        index=True,
        nullable=False,
    )
    entity_type: Mapped[SyncEntityType] = mapped_column(
        SAEnum(SyncEntityType, values_callable=lambda e: [m.value for m in e]),
        index=True,
        nullable=False,
    )
    entity_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    action: Mapped[SyncAction] = mapped_column(
        SAEnum(SyncAction, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    status: Mapped[SyncStatus] = mapped_column(
        SAEnum(SyncStatus, values_callable=lambda e: [m.value for m in e]),
        default=SyncStatus.PENDING,
        index=True,
        nullable=False,
    )
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
