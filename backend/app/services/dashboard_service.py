"""Servico de dashboard.

Agrega metricas do dominio (`services.friendship`) em tres visoes:
- `summary`: numeros gerais e listas auxiliares para a home
- `overdue`: amigos cujo proximo ping esta negativo
- `clusters`: amigos agrupados por interesse compartilhado

Carrega todos os amigos uma vez e hidrata em memoria — o app e single-user
com volume pequeno (ordem de centenas), entao nao vale complicar com
agregacao no SQL. Quando o volume crescer, dda pra migrar para queries
dedicadas sem mudar o contrato da API.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.friend import Friend
from app.models.group import FriendGroup
from app.schemas.dashboard import (
    DashboardClustersResponse,
    DashboardOverdueResponse,
    DashboardSummary,
    InterestCluster,
)
from app.schemas.friend import FriendRead
from app.services.friend_service import to_read
from app.services.friendship import cluster_by_interest, is_overdue


async def _load_all_friends(session: AsyncSession) -> list[Friend]:
    # tags + groups sao usados por to_read via selectinload; manter alinhado
    # com friend_service._friend_loaders pra evitar lazy load em async.
    stmt = (
        select(Friend)
        .options(
            selectinload(Friend.tags),
            selectinload(Friend.groups).selectinload(FriendGroup.group),
        )
        .order_by(Friend.name)
    )
    result = await session.execute(stmt)
    return list(result.scalars().unique().all())


def _hydrate(friends: list[Friend]) -> list[FriendRead]:
    return [to_read(f) for f in friends]


async def get_summary(session: AsyncSession) -> DashboardSummary:
    """Numeros gerais + listas auxiliares para a home.

    - `friends_by_temperature`: todos ordenados da mais quente para a mais
      fria (desempate alfabetico para estabilidade da UI)
    - `overdue_friends`: subconjunto com `days_until_next_ping < 0`,
      ordenados do mais atrasado para o menos atrasado
    """
    friends = await _load_all_friends(session)
    hydrated = _hydrate(friends)

    total = len(hydrated)
    avg_temp = (
        round(sum(f.temperature for f in hydrated) / total) if total else 0
    )
    by_temp = sorted(hydrated, key=lambda f: (-f.temperature, f.name))
    overdue = sorted(
        [f for f in hydrated if is_overdue(f.days_until_next_ping or 0)],
        key=lambda f: (f.days_until_next_ping or 0, f.name),
    )

    # interesses unicos = quantas tags distintas existem entre os amigos
    all_tags: set[str] = set()
    for f in hydrated:
        all_tags.update(f.tags)

    return DashboardSummary(
        total_friends=total,
        overdue_count=len(overdue),
        total_interests=len(all_tags),
        average_temperature=avg_temp,
        friends_by_temperature=by_temp,
        overdue_friends=overdue,
    )


async def get_overdue(session: AsyncSession) -> DashboardOverdueResponse:
    """Apenas a lista de atrasados, para telas focadas no bloco de atencao."""
    friends = await _load_all_friends(session)
    hydrated = _hydrate(friends)
    overdue = sorted(
        [f for f in hydrated if is_overdue(f.days_until_next_ping or 0)],
        key=lambda f: (f.days_until_next_ping or 0, f.name),
    )
    return DashboardOverdueResponse(friends=overdue)


async def get_clusters(session: AsyncSession) -> DashboardClustersResponse:
    """Clusters de amigos por interesse compartilhado.

    Usa `friendship.cluster_by_interest` (minimo 2 amigos por tag).
    """
    friends = await _load_all_friends(session)
    hydrated = _hydrate(friends)
    by_id: dict[int, FriendRead] = {f.id: f for f in hydrated}

    # pares (friend_id, tag) para alimentar a funcao pura
    pairs: list[tuple[int, str]] = []
    for f in hydrated:
        for tag in f.tags:
            pairs.append((f.id, tag))

    grouped = cluster_by_interest(pairs)
    clusters: list[InterestCluster] = []
    # ordena por tamanho do cluster desc, desempate alfabetico pela tag
    for tag in sorted(grouped, key=lambda t: (-len(grouped[t]), t)):
        ids = grouped[tag]
        cluster_friends = sorted(
            (by_id[i] for i in ids if i in by_id),
            key=lambda f: f.name,
        )
        clusters.append(InterestCluster(tag=tag, friends=cluster_friends))

    return DashboardClustersResponse(clusters=clusters)
