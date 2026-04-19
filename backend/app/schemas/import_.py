"""Schemas de importacao de contatos (CSV / VCF)."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.models.friend import Cadence, Category

# Campos canonicos que o usuario pode mapear colunas/atributos para.
# "ignore" significa que a coluna/campo nao sera usada no import.
ImportField = Literal["name", "phone", "email", "birthday", "notes", "tags", "ignore"]


class ImportCandidate(BaseModel):
    """Contato detectado no arquivo, pronto pra ser importado ou descartado."""

    # Indice da linha no arquivo de origem, usado pelo frontend para selecao.
    source_index: int
    name: str
    phone: str | None = None
    email: str | None = None
    birthday: date | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class ImportPreview(BaseModel):
    """Resposta do endpoint de preview de importacao."""

    total: int
    candidates: list[ImportCandidate] = Field(default_factory=list)
    # Headers detectados (CSV) ou campos encontrados (VCF), para exibicao.
    detected_fields: list[str] = Field(default_factory=list)
    # Mapeamento sugerido (CSV) header -> campo canonico, vazio em VCF.
    suggested_mapping: dict[str, ImportField] = Field(default_factory=dict)


class ImportCommit(BaseModel):
    """Payload de confirmacao de importacao.

    O frontend envia os indices aprovados e o mapeamento de categoria e
    cadencia padrao a aplicar nos contatos criados. Em CSV, `mapping` e
    obrigatorio (header -> campo canonico). Em VCF e ignorado.
    """

    approved_indexes: list[int]
    default_category: Category
    default_cadence: Cadence
    mapping: dict[str, ImportField] | None = None


class ImportCommitResponse(BaseModel):
    """Resultado da importacao efetiva."""

    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)
