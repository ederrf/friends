"""Servico de importacao de contatos.

13.10 (CSV) + 13.11 (VCF). Parsers sao puros em modulo dedicado para
que o router seja apenas um adaptador HTTP e os testes cubram os
formatos sem subir a stack.

Fluxo CSV:
1. `parse_csv(text)` → headers + rows (dicts header→string).
2. `guess_field(header)` → heuristica que mapeia headers comuns
   (Google Contacts, Outlook em pt/en) para o campo canonico do dominio.
3. `build_candidates(headers, rows, mapping)` → aplica mapeamento e
   produz `ImportCandidate`s, descartando linhas sem `name`.
4. `preview_csv(text)` e `commit_csv(session, text, payload)`.

Fluxo VCF:
1. `parse_vcf(text)` → lista de dicts ja com campos canonicos.
2. `preview_vcf(text)` devolve candidatos direto (nao ha mapping —
   o vCard tem nomes de campo padronizados).
3. `commit_vcf(session, text, payload)` persiste os aprovados.
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


async def _persist_approved(
    session: AsyncSession,
    candidates: list[ImportCandidate],
    payload: ImportCommit,
    *,
    unit_label: str,
) -> ImportCommitResponse:
    """Persiste candidatos aprovados, agregando erros por entrada.

    Compartilhado entre CSV e VCF — o formato de origem muda o rotulo do
    erro (`unit_label` = "linha" ou "contato") mas a regra e a mesma.
    """
    by_index = {c.source_index: c for c in candidates}
    imported = 0
    skipped = 0
    errors: list[str] = []
    for idx in payload.approved_indexes:
        cand = by_index.get(idx)
        if cand is None:
            skipped += 1
            errors.append(f"{unit_label} {idx}: candidato invalido ou sem nome.")
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
        except Exception as exc:  # noqa: BLE001 — agrega erro por entrada
            skipped += 1
            errors.append(f"{unit_label} {idx} ({cand.name}): {exc}")

    return ImportCommitResponse(imported=imported, skipped=skipped, errors=errors)


async def commit_csv(
    session: AsyncSession,
    text: str,
    payload: ImportCommit,
) -> ImportCommitResponse:
    """Persiste os candidatos CSV selecionados."""
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
    return await _persist_approved(session, candidates, payload, unit_label="linha")


# ── VCF (vCard) ──────────────────────────────────────────────────

# vCard (RFC 6350 + variantes 2.1/3.0 comuns em exports) tem estrutura:
#
#   BEGIN:VCARD
#   VERSION:3.0
#   FN:Ana Silva
#   N:Silva;Ana;;;
#   TEL;TYPE=CELL:+5511999990000
#   EMAIL;TYPE=HOME:ana@example.com
#   BDAY:19900315
#   NOTE:Amiga de longa data
#   CATEGORIES:rpg,cerveja
#   END:VCARD
#
# Notas de parsing:
# - Propriedades podem ter parametros depois de `;` (ex: `TEL;TYPE=CELL:...`)
# - Linhas dobradas (line-folding) comecam com espaco ou tab e continuam
#   a linha anterior. Fazemos o unfold antes de dividir em propriedades.
# - Valores podem ser escapados com `\n`, `\,`, `\;`, `\\` (RFC 6350 § 3.4).


_VCARD_ESCAPES: tuple[tuple[str, str], ...] = (
    ("\\n", "\n"),
    ("\\N", "\n"),
    ("\\,", ","),
    ("\\;", ";"),
    ("\\\\", "\\"),
)


def _unescape_value(raw: str) -> str:
    out = raw
    for esc, repl in _VCARD_ESCAPES:
        out = out.replace(esc, repl)
    return out


def _unfold_vcf(text: str) -> list[str]:
    """Aplica line-folding reverso: linha iniciada por espaco/tab se
    junta a anterior (RFC 6350 § 3.2)."""
    if not text:
        return []
    raw_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    folded: list[str] = []
    for line in raw_lines:
        if line.startswith((" ", "\t")) and folded:
            folded[-1] += line[1:]
        else:
            folded.append(line)
    return folded


def _split_property(line: str) -> tuple[str, dict[str, str], str] | None:
    """Divide `TEL;TYPE=CELL:+55...` em `("TEL", {"TYPE": "CELL"}, "+55...")`."""
    if ":" not in line:
        return None
    head, _, value = line.partition(":")
    parts = head.split(";")
    name = parts[0].upper()
    params: dict[str, str] = {}
    for p in parts[1:]:
        if "=" in p:
            k, _, v = p.partition("=")
            params[k.upper()] = v
        else:
            # parametro sem valor (ex: `TEL;CELL:...` do vCard 2.1)
            params.setdefault("TYPE", p)
    return name, params, value


def _name_from_n(value: str) -> str:
    """Converte `N:Silva;Ana;;;` em `"Ana Silva"` (given + family)."""
    parts = value.split(";")
    # ordem do vCard: Family;Given;Additional;Prefix;Suffix
    family = parts[0].strip() if len(parts) > 0 else ""
    given = parts[1].strip() if len(parts) > 1 else ""
    additional = parts[2].strip() if len(parts) > 2 else ""
    joined = " ".join(p for p in (given, additional, family) if p)
    return joined.strip()


def _decode_quoted_printable(value: str, params: dict[str, str]) -> str:
    """Alguns exports (Outlook/vCard 2.1) usam ENCODING=QUOTED-PRINTABLE."""
    if params.get("ENCODING", "").upper() != "QUOTED-PRINTABLE":
        return value
    charset = params.get("CHARSET", "utf-8")
    try:
        import quopri

        decoded = quopri.decodestring(value.encode("ascii", errors="replace"))
        return decoded.decode(charset, errors="replace")
    except Exception:  # noqa: BLE001
        return value


def _parse_vcard(block: list[str]) -> dict[str, object] | None:
    """Transforma as propriedades de um vCard em dict canonico.

    Retorna `None` se nao houver nome utilizavel.
    """
    fn = ""
    name_from_n = ""
    phone = ""
    email = ""
    birthday_raw = ""
    notes = ""
    tags: list[str] = []

    for line in block:
        parsed = _split_property(line)
        if parsed is None:
            continue
        name, params, value = parsed
        value = _decode_quoted_printable(value, params)
        value = _unescape_value(value).strip()
        if name == "FN" and not fn:
            fn = value
        elif name == "N" and not name_from_n:
            name_from_n = _name_from_n(value)
        elif name == "TEL" and not phone:
            phone = value
        elif name == "EMAIL" and not email:
            email = value
        elif name == "BDAY" and not birthday_raw:
            birthday_raw = value
        elif name == "NOTE" and not notes:
            notes = value
        elif name == "CATEGORIES":
            tags.extend(_split_tags(value))

    display_name = fn or name_from_n
    if not display_name:
        return None

    return {
        "name": display_name,
        "phone": phone or None,
        "email": email or None,
        "birthday": parse_birthday(birthday_raw) if birthday_raw else None,
        "notes": notes or None,
        "tags": tags,
    }


def parse_vcf(text: str) -> list[ImportCandidate]:
    """Le um texto vCard e devolve os candidatos extraidos.

    `source_index` e o indice do vCard dentro do arquivo (0-based),
    considerando apenas blocos validos; candidatos sem nome sao
    descartados mas o indice dos restantes e preservado.
    """
    lines = _unfold_vcf(text)
    candidates: list[ImportCandidate] = []
    current: list[str] | None = None
    card_index = -1
    for line in lines:
        stripped = line.strip()
        if stripped.upper() == "BEGIN:VCARD":
            current = []
            card_index += 1
            continue
        if stripped.upper() == "END:VCARD":
            if current is not None:
                parsed = _parse_vcard(current)
                if parsed is not None:
                    candidates.append(
                        ImportCandidate(
                            source_index=card_index,
                            name=str(parsed["name"]),
                            phone=parsed["phone"],  # type: ignore[arg-type]
                            email=parsed["email"],  # type: ignore[arg-type]
                            birthday=parsed["birthday"],  # type: ignore[arg-type]
                            notes=parsed["notes"],  # type: ignore[arg-type]
                            tags=list(parsed["tags"]),  # type: ignore[arg-type]
                        )
                    )
            current = None
            continue
        if current is not None and stripped:
            current.append(stripped)
    return candidates


def preview_vcf(text: str) -> ImportPreview:
    """Preview de VCF. `detected_fields` e `suggested_mapping` ficam vazios
    porque vCard tem nomes padronizados — nao ha mapping a editar."""
    candidates = parse_vcf(text)
    return ImportPreview(
        total=len(candidates),
        candidates=candidates,
        detected_fields=[],
        suggested_mapping={},
    )


async def commit_vcf(
    session: AsyncSession,
    text: str,
    payload: ImportCommit,
) -> ImportCommitResponse:
    """Persiste os contatos VCF selecionados."""
    candidates = parse_vcf(text)
    if not candidates:
        raise AppError(
            code="IMPORT_EMPTY_FILE",
            message="Arquivo VCF sem contatos validos.",
        )
    return await _persist_approved(session, candidates, payload, unit_label="contato")
