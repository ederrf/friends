"""Regras de dominio de amizade.

Concentra calculos puros usados pelo dashboard, pela API de amigos e pelos
testes: temperatura, dias sem contato, proximo ping, clusters por interesse
e ganchos de conversa.

Manter estas funcoes puras (sem acesso a DB) torna os testes diretos.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.friend import Cadence

# ── Cadencias em dias (PRD 7.2) ─────────────────────────────────
CADENCE_DAYS: dict[Cadence, int] = {
    Cadence.WEEKLY: 7,
    Cadence.BIWEEKLY: 14,
    Cadence.MONTHLY: 30,
    Cadence.QUARTERLY: 90,
}

# Faixas de temperatura (PRD 7.3).
TEMPERATURE_LABELS: list[tuple[int, str]] = [
    (75, "Quente"),
    (50, "Morna"),
    (25, "Esfriando"),
    (0, "Fria"),
]


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.timezone)


def _now() -> datetime:
    return datetime.now(_tz())


def _aware(dt: datetime) -> datetime:
    """Converte datetime naive (vindo do SQLite) para o timezone do app."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=_tz())
    return dt.astimezone(_tz())


@dataclass
class FriendMetrics:
    """Metricas derivadas de uma amizade em um instante."""

    days_since_last_contact: int | None
    days_until_next_ping: int | None
    temperature: int
    temperature_label: str


def days_since_last_contact(
    last_contact_at: datetime | None,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> int:
    """Dias desde o ultimo contato.

    Se `last_contact_at` for nulo, usa `created_at` como referencia. A UI
    trata "amigo sem contato desde que foi criado" como se fosse contato na
    criacao: nao e bom nem ruim, apenas reflete o estado inicial.
    """
    reference = last_contact_at if last_contact_at is not None else created_at
    reference = _aware(reference)
    current = now or _now()
    current = _aware(current)
    delta = (current - reference).days
    return max(0, delta)


def days_until_next_ping(
    cadence: Cadence,
    last_contact_at: datetime | None,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> int:
    """Dias ate o proximo ping recomendado.

    Negativo quando o amigo esta atrasado.
    """
    elapsed = days_since_last_contact(last_contact_at, created_at, now=now)
    return CADENCE_DAYS[cadence] - elapsed


def calculate_temperature(
    cadence: Cadence,
    last_contact_at: datetime | None,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> int:
    """Temperatura da amizade no intervalo [0, 100].

    Formula PRD 7.3:
      temperatura = (1 - dias / (cadencia_dias * 2.5)) * 100
    """
    elapsed = days_since_last_contact(last_contact_at, created_at, now=now)
    cadence_days = CADENCE_DAYS[cadence]
    raw = (1 - elapsed / (cadence_days * 2.5)) * 100
    return int(max(0, min(100, round(raw))))


def temperature_label(value: int) -> str:
    """Rotulo textual da faixa de temperatura."""
    for threshold, label in TEMPERATURE_LABELS:
        if value >= threshold:
            return label
    return "Fria"


def compute_friend_metrics(
    cadence: Cadence,
    last_contact_at: datetime | None,
    created_at: datetime,
    *,
    now: datetime | None = None,
) -> FriendMetrics:
    """Calcula todas as metricas derivadas de uma amizade de uma vez."""
    days = days_since_last_contact(last_contact_at, created_at, now=now)
    next_ping = days_until_next_ping(cadence, last_contact_at, created_at, now=now)
    temp = calculate_temperature(cadence, last_contact_at, created_at, now=now)
    return FriendMetrics(
        days_since_last_contact=days,
        days_until_next_ping=next_ping,
        temperature=temp,
        temperature_label=temperature_label(temp),
    )


def is_overdue(next_ping_days: int) -> bool:
    """Amigo esta atrasado quando o proximo ping esta negativo."""
    return next_ping_days < 0


# ── Clusters e ganchos de conversa ──────────────────────────────


def cluster_by_interest(
    friend_tags: list[tuple[int, str]],
    *,
    min_cluster_size: int = 2,
) -> dict[str, list[int]]:
    """Agrupa ids de amigos por tag compartilhada.

    Recebe lista de pares `(friend_id, tag)` e devolve `{tag: [friend_ids]}`.
    Por padrao so inclui tags com pelo menos `min_cluster_size` amigos,
    porque cluster de 1 pessoa nao e cluster.
    """
    buckets: dict[str, set[int]] = defaultdict(set)
    for friend_id, tag in friend_tags:
        buckets[tag].add(friend_id)

    return {
        tag: sorted(ids)
        for tag, ids in buckets.items()
        if len(ids) >= min_cluster_size
    }


def unique_interests(friend_tags: list[tuple[int, str]]) -> list[str]:
    """Tags que aparecem em apenas um amigo."""
    counts: dict[str, int] = defaultdict(int)
    for _, tag in friend_tags:
        counts[tag] += 1
    return sorted(tag for tag, count in counts.items() if count == 1)


def conversation_hooks(
    friend_id: int,
    friend_tags: list[tuple[int, str]],
    *,
    limit: int = 5,
) -> list[str]:
    """Ganchos de conversa: tags deste amigo compartilhadas com outros.

    Ordena por frequencia decrescente (tags que mais aparecem em outros
    amigos aparecem primeiro, porque sao pontes sociais mais fortes).
    """
    own_tags = {tag for fid, tag in friend_tags if fid == friend_id}
    if not own_tags:
        return []

    shared_counts: dict[str, int] = defaultdict(int)
    for fid, tag in friend_tags:
        if fid == friend_id:
            continue
        if tag in own_tags:
            shared_counts[tag] += 1

    ranked = sorted(shared_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [tag for tag, _ in ranked[:limit]]
