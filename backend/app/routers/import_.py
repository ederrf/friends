"""Routers de importacao (PRD 9.5).

Endpoints aceitam upload `multipart/form-data` para nao precisar
serializar o conteudo do arquivo em base64. O `payload` JSON do commit
vem como `Form(...)` ao lado do arquivo.

VCF (13.11) ainda nao foi implementado — sera adicionado na proxima
iteracao usando a mesma estrutura.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import AppError
from app.schemas.import_ import (
    ImportCommit,
    ImportCommitResponse,
    ImportPreview,
)
from app.services import import_service

router = APIRouter(prefix="/api/import", tags=["import"])

# Limite generoso pra contatos exportados (~10MB cobre 50k linhas).
_MAX_FILE_BYTES = 10 * 1024 * 1024


async def _read_text(file: UploadFile) -> str:
    raw = await file.read()
    if len(raw) > _MAX_FILE_BYTES:
        raise AppError(
            code="IMPORT_FILE_TOO_LARGE",
            message="Arquivo excede o limite de 10 MB.",
            details={"size": len(raw), "limit": _MAX_FILE_BYTES},
        )
    # Exports do Windows costumam vir em UTF-8 com BOM ou Latin-1.
    # `errors="replace"` evita que um byte ruim aborte o import inteiro.
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1", errors="replace")


def _parse_mapping(raw: str | None) -> dict[str, str] | None:
    if raw is None or raw == "":
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AppError(
            code="IMPORT_BAD_MAPPING",
            message="Mapeamento JSON invalido.",
            details={"reason": str(exc)},
        ) from exc
    if not isinstance(parsed, dict):
        raise AppError(
            code="IMPORT_BAD_MAPPING",
            message="Mapeamento deve ser um objeto JSON.",
        )
    return parsed


@router.post("/csv/preview", response_model=ImportPreview)
async def csv_preview(
    file: UploadFile = File(...),
    mapping: str | None = Form(default=None),
) -> ImportPreview:
    """Le o CSV e devolve preview (sem persistir).

    `mapping` opcional: JSON `{"<header>": "<campo>"}`. Quando ausente,
    a autodeteccao gera `suggested_mapping` que o frontend pode editar.
    """
    text = await _read_text(file)
    parsed_mapping = _parse_mapping(mapping)
    return import_service.preview_csv(text, parsed_mapping)


@router.post("/csv/commit", response_model=ImportCommitResponse)
async def csv_commit(
    file: UploadFile = File(...),
    payload: str = Form(...),
    session: AsyncSession = Depends(get_db),
) -> ImportCommitResponse:
    """Persiste os candidatos selecionados.

    `payload` e um JSON serializado de `ImportCommit` (multipart nao
    aceita JSON direto em campos nao-arquivo).
    """
    text = await _read_text(file)
    try:
        commit = ImportCommit.model_validate_json(payload)
    except ValueError as exc:
        raise AppError(
            code="IMPORT_BAD_PAYLOAD",
            message="Payload de confirmacao invalido.",
            details={"reason": str(exc)},
        ) from exc
    return await import_service.commit_csv(session, text, commit)
