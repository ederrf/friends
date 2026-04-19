"""Schemas de interacao."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.interaction import InteractionType


class InteractionCreate(BaseModel):
    """Payload de nova interacao.

    `occurred_at` e opcional: quando ausente, o servico usa `now()`.
    Isso torna o registro rapido em um toque na UI.
    """

    occurred_at: datetime | None = None
    note: str | None = Field(default=None, max_length=2000)
    interaction_type: InteractionType = InteractionType.OTHER


class InteractionRead(BaseModel):
    """Interacao serializada."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    friend_id: int
    occurred_at: datetime
    note: str | None = None
    interaction_type: InteractionType
    created_at: datetime
