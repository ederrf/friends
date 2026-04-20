"""Schemas do log de sincronizacao com provedores externos."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.models.sync_event import (
    SyncAction,
    SyncEntityType,
    SyncProvider,
    SyncStatus,
)


class SyncEventRead(BaseModel):
    """Leitura de `sync_event` para resposta da API de integracoes."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    provider: SyncProvider
    entity_type: SyncEntityType
    entity_id: int | None
    action: SyncAction
    status: SyncStatus
    external_id: str | None
    payload_json: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
