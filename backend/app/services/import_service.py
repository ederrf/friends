"""Servico de importacao de contatos.

13.10 — implementa o lado CSV. O parser e em servico dedicado para que o
router seja apenas um adaptador HTTP e os testes possam exercitar os
formatos diretamente.

Fluxo:
1. `parse_csv(text)` → headers + rows (dicts header→string).
2. `guess_field(header)` → heuristica que mapeia headers comuns
   (Google Contacts, Outlook em pt/en) para o campo canonico do dominio.
3. `build_candidates(headers, rows, mapping)` → aplica mapeamento e
   produz `ImportCandidate`s, descartando linhas sem `name`.
4. `preview_csv(text)` e `commit_csv(session, text, payload)` empacotam
   tudo para o router.

VCF chega na 13.11. Ja deixei o esqueleto preparado pra reuso.
"""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import AppError
from app.schemas.friend import FriendCreate
from app.schemas.import_ import (
    ImportCandidate,
    ImportCommit,
    ImportCommitResponse,
    ImportField,
    ImportPreview,
)
from app.services import friend_service

# ── Auto-deteccao de colunas ─────────────────────────────────────

# Cada campo canonico tem uma lista de prefixos (ja normalizados) que
# costumam aparecer em exports de Google Contacts, Outlook, planilhas em
# pt-BR. A primeira correspondencia ganha — campos mais especificos
# (ex: "tags") devem ficar antes de mais genericos no dict.
_FIELD_PREFIXES: dict[ImportField, tuple[str, ...]] = {
    "name": (
        "name",
        "nome",
        "fullname",
        "nomecompleto",
        "fn",
        "displayname",
        "firstname",
        "primeironome",
    ),
    "phone": (
        "phone",
        "tel",
        "telefone",
        "celular",
        "mobile",
        "whatsapp",
        "cel",
    ),
    "email": (
        "email",
        "emailaddress",
        "correio",
        "mail",
    ),
    "birthday": (
        "birth",
        "birthday",
        "aniversario",
        "nascimento",
        "bday",
        "dob",
        "datanasc",
        "datadenascimento",
    ),
    "notes": (
        "note",
        "notes",
        "notas",
        "obs",
        "observa",
        "comment",
        "coment",
    ),
    "tags": (
        "tag",
        "tags",
        "grupo",
        "grupos",
        "label",
        "labels",
        "categoria",
        "category",
    ),
}


def _normalize_header(header: str) -> str:
    """Lowercase + remove tudo que nao e a-z/0-9 (mantem prefixo curto)."""
    return re.sub(r"[^a-z0-9]", "", header.lower())


def guess_field(header: str) -> ImportField:
    """Mapeia um header de coluna para um campo canonico.

    Retorna `"ignore"` quando nenhum prefixo conhecido bate. O usuario
    pode sobrescrever no frontend.
    """
    norm = _normalize_header(header)
    if not norm:
        return "ignore"
    for field, prefixes in _FIELD_PREFIXES.items():
        for prefix in prefixes:
            if norm.startswith(prefix):
                return field
    return "ignore"


# ── Parser CSV ───────────────────────────────────────────────────


def _detect_dialect(sample: str) -> type[csv.Dialect] | csv.Dialect:
    """Detecta separador (`,`, `;`, `\\t`) com fallback para excel."""
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


def parse_csv(text: str) -> tuple[list[str], list[dict[str, str]]]:
    """Le um CSV e devolve `(headers, rows)`.

    - Strips BOM (`\\ufeff`) que vem em exports do Excel/Google.
    - Detecta separador automaticamente.
    - Linhas totalmente vazias sao descartadas.
    - Headers tambem sao trimados; rows preservam as chaves originais.
    """
    if not text:
        return [], []
    text = text.lstrip("\ufeff")
    sample = text[:2048]
    dialect = _detect_dialect(sample)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    headers = [h.strip() for h in (reader.fieldnames or [])]
    if not headers:
        return [], []
    rows: list[dict[str, str]] = []
    for raw in reader:
        # DictReader pode produzir None em chaves quando linhas tem mais
        # colunas que o header — descartamos.
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        rows.append(row)
    return headers, rows


# ── Normalizacao de valores ──────────────────────────────────────

# Aceitamos varios formatos comuns de data. A ordem importa porque
# `2024-01-02` casaria com DD/MM se invertessemos.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%Y%m%d",
)


def parse_birthday(raw: str) -> date | None:
    """Tenta converter a string em `date`. Ignora silenciosamente."""
    raw = raw.strip()
    if not raw:
        return None
    # vCard usa --MM-DD para datas sem ano; ignoramos por enquanto
    # (Friend.birthday e nullable, melhor que importar lixo).
    if raw.startswith("--"):
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    # Fallback: tenta ISO completo (datetime → date).
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None


def _split_tags(raw: str) -> list[str]:
    """Tags vem separadas por virgula, ponto e virgula ou pipe."""
    parts = re.split(r"[,;|]", raw)
    out: list[str] = []
    seen: set[str] = set()
    for p in parts:
        norm = p.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


# ── Construcao de candidatos ─────────────────────────────────────


def _build_candidate(
    source_index: int,
    row: dict[str, str],
    mapping: dict[str, ImportField],
) -> ImportCandidate | None:
    """Aplica `mapping` a uma linha. Retorna `None` se nao tiver `name`.

    Campos com mapeamento duplicado (ex: dois headers → "phone") usam o
    PRIMEIRO valor nao-vazio, na ordem do dict de mapping.
    """
    bucket: dict[str, str] = {}
    tags: list[str] = []
    for header, field in mapping.items():
        if field == "ignore":
            continue
        value = row.get(header, "").strip()
        if not value:
            continue
        if field == "tags":
            tags.extend(_split_tags(value))
            continue
        # nao sobrescreve campos ja preenchidos por header anterior
        if field not in bucket:
            bucket[field] = value

    name = bucket.get("name", "").strip()
    if not name:
        return None

    return ImportCandidate(
        source_index=source_index,
        name=name,
        phone=bucket.get("phone") or None,
        email=bucket.get("email") or None,
        birthday=parse_birthday(bucket.get("birthday", "")),
        notes=bucket.get("notes") or None,
        tags=tags,
    )


def build_candidates(
    headers: list[str],
    rows: list[dict[str, str]],
    mapping: dict[str, ImportField] | None = None,
) -> tuple[list[ImportCandidate], dict[str, ImportField]]:
    """Constroi candidatos. Se `mapping` for None, usa autodeteccao."""
    effective: dict[str, ImportField] = (
        dict(mapping) if mapping is not None else {h: guess_field(h) for h in headers}
    )
    candidates: list[ImportCandidate] = []
    for idx, row in enumerate(rows):
        cand = _build_candidate(idx, row, effective)
        if cand is not None:
            candidates.append(cand)
    return candidates, effective


# ── API pro router ───────────────────────────────────────────────


def preview_csv(text: str, mapping: dict[str, ImportField] | None = None) -> ImportPreview:
    """Parseia o CSV e devolve preview (sem persistir nada)."""
    headers, rows = parse_csv(text)
    candidates, effective_mapping = build_candidates(headers, rows, mapping)
    return ImportPreview(
        total=len(candidates),
        candidates=candidates,
        detected_fields=headers,
        suggested_mapping=effective_mapping,
    )


async def commit_csv(
    session: AsyncSession,
    text: str,
    payload: ImportCommit,
) -> ImportCommitResponse:
    """Persiste os candidatos selecionados.

    Erros por linha sao acumulados em `errors` (mensagem curta), nao
    abortam o resto. Falha de DB no commit final propaga.
    """
    headers, rows = parse_csv(text)
    if not headers:
        raise AppError(
            code="IMPORT_EMPTY_FILE",
            message="Arquivo CSV vazio ou sem cabecalho.",
        )
    if payload.mapping is None:
        raise AppError(
            code="IMPORT_MAPPING_REQUIRED",
            message="Mapeamento de colunas e obrigatorio na confirmacao do CSV.",
        )

    candidates, _ = build_candidates(headers, rows, payload.mapping)
    by_index = {c.source_index: c for c in candidates}

    imported = 0
    skipped = 0
    errors: list[str] = []
    for idx in payload.approved_indexes:
        cand = by_index.get(idx)
        if cand is None:
            skipped += 1
            errors.append(f"linha {idx}: candidato invalido ou sem nome.")
            continue
        try:
            await friend_service.create_friend(
                session,
                FriendCreate(
                    name=cand.name,
                    phone=cand.phone,
                    email=cand.email,
                    birthday=cand.birthday,
                    notes=cand.notes,
                    category=payload.default_category,
                    cadence=payload.default_cadence,
                    tags=cand.tags,
                ),
            )
            imported += 1
        except Exception as exc:  # noqa: BLE001 — agrega erro por linha
            skipped += 1
            errors.append(f"linha {idx} ({cand.name}): {exc}")

    return ImportCommitResponse(imported=imported, skipped=skipped, errors=errors)
