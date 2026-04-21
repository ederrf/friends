"""Schemas (request/response contracts) de Friend."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.friend import Cadence, Category
from app.schemas.group import GroupRef


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
    groups: list[GroupRef] = Field(default_factory=list)

    # ── Campos derivados (preenchidos pelo servico de dominio) ──
    days_since_last_contact: int | None = None
    days_until_next_ping: int | None = None
    temperature: int = 100
    temperature_label: str = "Quente"


# ── Bulk actions ─────────────────────────────────────────────────


class BulkIdsPayload(BaseModel):
    """Lista de ids para operacao em lote.

    Limite superior protege contra payloads patologicos (timeout, lock).
    Se precisar apagar mais que `max_length`, chame o endpoint em blocos.
    """

    ids: list[int] = Field(..., min_length=1, max_length=500)


class BulkTagPayload(BulkIdsPayload):
    """Lista de ids + tag para aplicar/remover em lote."""

    tag: str = Field(..., min_length=1, max_length=80)


class BulkOpResult(BaseModel):
    """Resumo uniforme de operacoes em lote.

    - `affected`: quantos de fato mudaram (deletados, atualizados, taggeados).
    - `not_found`: ids que nao existem no banco — silenciosos por
      definicao (coerente com apagar em massa apos import onde o usuario
      pode desmarcar entre clicks).
    - `skipped`: ids que existiam mas eram no-op (ex.: ja tinham a tag).
    """

    affected: int
    not_found: list[int] = Field(default_factory=list)
    skipped: list[int] = Field(default_factory=list)


# ── Merge ────────────────────────────────────────────────────────


class MergePayload(BaseModel):
    """Funde varios amigos (sources) em um primario.

    `primary_id` e o amigo que sera preservado; `source_ids` sao fundidos
    nele e deletados ao final. Ids duplicados e a presenca do `primary_id`
    dentro de `source_ids` sao tratados silenciosamente pelo servico.
    """

    primary_id: int = Field(..., gt=0)
    source_ids: list[int] = Field(..., min_length=1, max_length=50)


class MergeResult(BaseModel):
    """Resposta do merge, com o amigo resultante ja hidratado."""

    friend: FriendRead
    merged: int  # sources efetivamente fundidos
    not_found: list[int] = Field(default_factory=list)
    interactions_moved: int
    tags_added: int
