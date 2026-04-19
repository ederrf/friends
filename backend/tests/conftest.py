"""Fixtures compartilhadas de testes.

Estrategia:
- cada teste usa um banco SQLite em arquivo temporario proprio
- override da dependencia `get_db` para usar a sessao do teste
- httpx AsyncClient com ASGITransport para chamar a API em processo

Usar um arquivo temporario em vez de `:memory:` garante que conexoes
diferentes vejam as mesmas tabelas (SQLite :memory: e por-conexao).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture
async def engine(tmp_path: Path):
    db_path = tmp_path / "test.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(url, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as s:
        yield s


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def friend_payload() -> dict:
    """Payload valido reutilizavel nos testes de CRUD."""
    return {
        "name": "Marcelo Silva",
        "phone": "(11) 98765-4321",
        "email": "marcelo@example.com",
        "birthday": "1990-03-15",
        "category": "rekindle",
        "cadence": "monthly",
        "notes": "Amigo da faculdade.",
        "tags": ["RPG", "Cerveja", "rpg"],  # dup para testar normalizacao
    }
