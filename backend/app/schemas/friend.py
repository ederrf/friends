"""Schemas (request/response contracts) de Friend."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.friend import Cadence, Category


class FriendBase(BaseModel):
    """Campos compartilhados entre create e update."""

    name: str = Field(..., min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    birthday: date | None = None
    category: Category
    cadence: Cadence
    notes: str | None = None


class FriendCreate(FriendBase):
    """Payload de criacao de amigo.

    Tags opcionais: quando presentes, sao criadas junto com o amigo no mesmo
    fluxo para economizar chamadas.
    """

    tags: list[str] = Field(default_factory=list)


class FriendUpdate(BaseModel):
    """Payload de atualizacao parcial."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    birthday: date | None = None
    category: Category | None = None
    cadence: Cadence | None = None
    notes: str | None = None


class FriendRead(FriendBase):
    """Amigo serializado para o frontend, com campos derivados."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    last_contact_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)

    # ── Campos derivados (preenchidos pelo servico de dominio) ──
    days_since_last_contact: int | None = None
    days_until_next_ping: int | None = None
    temperature: int = 100
    temperature_label: str = "Quente"
