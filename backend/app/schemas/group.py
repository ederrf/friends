"""Schemas (request/response contracts) de Group (13.23)."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Hex color no formato #RRGGBB — lowercase.
_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
DEFAULT_COLOR = "#64748b"  # slate-500 (neutro)


def _validate_hex_color(value: str) -> str:
    """Normaliza + valida cor no formato #RRGGBB."""
    value = value.strip()
    if not _HEX_COLOR_RE.match(value):
        raise ValueError("color deve ser hex no formato #RRGGBB")
    return value.lower()


class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    color: str = Field(default=DEFAULT_COLOR, max_length=16)

    @field_validator("color")
    @classmethod
    def _color(cls, v: str) -> str:
        return _validate_hex_color(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        # Preserva case original do usuario (ex: "RPG", "Familia") mas sem
        # whitespace nas pontas. Unicidade e case-insensitive no service.
        v = v.strip()
        if not v:
            raise ValueError("name vazio apos strip")
        return v


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    color: str | None = Field(default=None, max_length=16)

    @field_validator("color")
    @classmethod
    def _color(cls, v: str | None) -> str | None:
        return None if v is None else _validate_hex_color(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("name vazio apos strip")
        return v


class GroupRef(BaseModel):
    """Forma compacta de Group usada dentro de FriendRead.

    Carrega so o que a UI precisa pra renderizar um chip: id, nome, cor.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str


class GroupRead(GroupBase):
    """Group completo com metricas agregadas."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    member_count: int = 0
    created_at: datetime
    updated_at: datetime


class GroupMembership(BaseModel):
    """Payload para adicionar um amigo a um grupo (singular)."""

    friend_id: int = Field(..., gt=0)


class BulkFriendIdsPayload(BaseModel):
    """friend_ids em lote para bulk add/remove num grupo."""

    friend_ids: list[int] = Field(..., min_length=1, max_length=500)


class BulkGroupPayload(BaseModel):
    """Payload para bulk add/remove de grupo na rota de friends.

    Chave `ids` e consistente com os outros bulk de friends; `group_id`
    identifica o grupo alvo. Limite superior protege contra payloads
    patologicos (timeout/lock).
    """

    ids: list[int] = Field(..., min_length=1, max_length=500)
    group_id: int = Field(..., gt=0)
