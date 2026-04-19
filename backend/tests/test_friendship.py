"""Testes unitarios das regras de dominio (13.5)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.config import settings
from app.models.friend import Cadence
from app.services.friendship import (
    CADENCE_DAYS,
    calculate_temperature,
    cluster_by_interest,
    compute_friend_metrics,
    conversation_hooks,
    days_since_last_contact,
    days_until_next_ping,
    is_overdue,
    temperature_label,
    unique_interests,
)

TZ = ZoneInfo(settings.timezone)
NOW = datetime(2026, 4, 18, 12, 0, tzinfo=TZ)


def ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


# ── days_since_last_contact ─────────────────────────────────────


def test_days_since_last_contact_usa_last_contact_quando_disponivel():
    assert days_since_last_contact(ago(10), ago(100), now=NOW) == 10


def test_days_since_last_contact_usa_created_at_quando_last_for_nulo():
    assert days_since_last_contact(None, ago(7), now=NOW) == 7


def test_days_since_last_contact_nunca_negativo():
    # Defesa contra relogio fora de sync: um contato no futuro cai pra 0.
    future = NOW + timedelta(days=3)
    assert days_since_last_contact(future, ago(100), now=NOW) == 0


def test_days_since_last_contact_aceita_datetime_naive():
    # SQLite devolve datetimes naive; a funcao precisa lidar sem explodir.
    naive_last = (NOW - timedelta(days=5)).replace(tzinfo=None)
    naive_created = (NOW - timedelta(days=50)).replace(tzinfo=None)
    assert days_since_last_contact(naive_last, naive_created, now=NOW) == 5


# ── days_until_next_ping ────────────────────────────────────────


def test_next_ping_positivo_quando_dentro_da_cadencia():
    # monthly=30, contato ha 10 dias -> faltam 20
    assert days_until_next_ping(Cadence.MONTHLY, ago(10), ago(999), now=NOW) == 20


def test_next_ping_negativo_quando_atrasado():
    # weekly=7, contato ha 10 dias -> -3
    assert days_until_next_ping(Cadence.WEEKLY, ago(10), ago(999), now=NOW) == -3


def test_is_overdue():
    assert is_overdue(-1) is True
    assert is_overdue(0) is False
    assert is_overdue(5) is False


# ── temperatura ─────────────────────────────────────────────────


def test_temperatura_eh_100_quando_acabou_de_contatar():
    assert calculate_temperature(Cadence.MONTHLY, ago(0), ago(999), now=NOW) == 100


def test_temperatura_eh_0_alem_de_2_5x_a_cadencia():
    # monthly*2.5 = 75 dias. 100 dias garante 0.
    assert calculate_temperature(Cadence.MONTHLY, ago(100), ago(999), now=NOW) == 0


def test_temperatura_no_limite_exato_da_cadencia_eh_60():
    # No dia exato da cadencia: (1 - 30/75) * 100 = 60
    assert calculate_temperature(Cadence.MONTHLY, ago(30), ago(999), now=NOW) == 60


def test_temperatura_usa_created_at_quando_last_nulo():
    # Amigo recem-criado ha 1 dia deve estar quase em 100 pra monthly.
    temp = calculate_temperature(Cadence.MONTHLY, None, ago(1), now=NOW)
    assert 95 <= temp <= 100


@pytest.mark.parametrize(
    "value, label",
    [
        (100, "Quente"),
        (75, "Quente"),
        (74, "Morna"),
        (50, "Morna"),
        (49, "Esfriando"),
        (25, "Esfriando"),
        (24, "Fria"),
        (0, "Fria"),
    ],
)
def test_temperature_label(value, label):
    assert temperature_label(value) == label


def test_compute_friend_metrics_agrupa_tudo():
    m = compute_friend_metrics(Cadence.WEEKLY, ago(5), ago(100), now=NOW)
    assert m.days_since_last_contact == 5
    assert m.days_until_next_ping == 2
    assert m.temperature == calculate_temperature(
        Cadence.WEEKLY, ago(5), ago(100), now=NOW
    )
    assert m.temperature_label == temperature_label(m.temperature)


def test_cadence_days_cobre_todos_os_membros_do_enum():
    # Protege contra adicao de um novo valor de cadencia sem atualizar o mapa.
    assert set(CADENCE_DAYS) == set(Cadence)


# ── clusters e ganchos ──────────────────────────────────────────


def test_cluster_by_interest_agrupa_por_tag_e_ignora_solos():
    pairs = [
        (1, "rpg"),
        (2, "rpg"),
        (3, "rpg"),
        (1, "cinema"),
        (4, "musica"),  # solo, deve ser filtrado
    ]
    clusters = cluster_by_interest(pairs)
    assert clusters == {"rpg": [1, 2, 3]}


def test_cluster_by_interest_respeita_min_cluster_size():
    pairs = [(1, "rpg"), (2, "rpg"), (1, "cinema"), (3, "cinema")]
    clusters = cluster_by_interest(pairs, min_cluster_size=2)
    assert set(clusters) == {"rpg", "cinema"}


def test_unique_interests():
    pairs = [(1, "rpg"), (2, "rpg"), (3, "magic"), (4, "culinaria")]
    assert unique_interests(pairs) == ["culinaria", "magic"]


def test_conversation_hooks_ordena_por_frequencia_compartilhada():
    # Amigo 1 tem rpg, cinema, musica. rpg e compartilhado com 2 outros,
    # cinema com 1, musica com ninguem.
    pairs = [
        (1, "rpg"),
        (1, "cinema"),
        (1, "musica"),
        (2, "rpg"),
        (3, "rpg"),
        (4, "cinema"),
    ]
    hooks = conversation_hooks(1, pairs)
    assert hooks == ["rpg", "cinema"]


def test_conversation_hooks_sem_tags_retorna_vazio():
    pairs = [(2, "rpg")]
    assert conversation_hooks(1, pairs) == []


def test_conversation_hooks_limit():
    pairs = [(1, f"tag{i}") for i in range(10)]
    pairs += [(2, f"tag{i}") for i in range(10)]
    assert len(conversation_hooks(1, pairs, limit=3)) == 3
