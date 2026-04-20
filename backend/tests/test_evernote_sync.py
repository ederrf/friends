"""Testes da integracao Evernote via IFTTT (13.12).

Cobertura:
- `ifttt_client.trigger_webhook` com transport mock (sucesso/erro HTTP/config)
- `build_note_body` com e sem cabecalho de metadados
- `sync_interaction_to_evernote` sucesso (registra SUCCESS em sync_event)
- sync com falha (registra FAILED, propaga excecao, log sobrevive)
- cabecalho so no primeiro append — segundo append ja nao inclui
- 404 para friend/interaction inexistente
- endpoint HTTP com override do `ifttt_client.trigger_webhook`
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import httpx
import pytest
from sqlalchemy import select

from app.config import settings
from app.models.friend import Cadence, Category, Friend
from app.models.friend_tag import FriendTag
from app.models.interaction import Interaction, InteractionType
from app.models.sync_event import (
    SyncAction,
    SyncEntityType,
    SyncEvent,
    SyncProvider,
    SyncStatus,
)
from app.services import evernote_service, ifttt_client


# ── ifttt_client ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ifttt_trigger_webhook_sends_payload_and_returns_body():
    captured: dict = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["json"] = dict(request.json if hasattr(request, "json") else {})  # noqa
        # httpx.Request nao expoe .json; parsear manualmente
        import json

        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(200, text="Congratulations!")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        text = await ifttt_client.trigger_webhook(
            value1="Friends: Ana",
            value2="corpo",
            event="test_event",
            key="testkey",
            client=client,
        )

    assert text == "Congratulations!"
    assert captured["url"].endswith("/trigger/test_event/with/key/testkey")
    assert captured["body"] == {"value1": "Friends: Ana", "value2": "corpo"}


@pytest.mark.asyncio
async def test_ifttt_trigger_webhook_raises_on_4xx():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(401, text="Invalid key")
    )
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ifttt_client.IftttWebhookError) as excinfo:
            await ifttt_client.trigger_webhook(
                "t", event="e", key="k", client=client
            )
    assert excinfo.value.status_code == 502
    assert excinfo.value.details["provider_status"] == 401


@pytest.mark.asyncio
async def test_ifttt_trigger_webhook_raises_on_network_error():
    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(boom)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ifttt_client.IftttWebhookError):
            await ifttt_client.trigger_webhook(
                "t", event="e", key="k", client=client
            )


@pytest.mark.asyncio
async def test_ifttt_trigger_webhook_missing_key_raises_config_error():
    with pytest.raises(ifttt_client.IftttConfigError):
        await ifttt_client.trigger_webhook("t", event="e", key="")


# ── build_note_body ──────────────────────────────────────────────


def _make_friend() -> Friend:
    f = Friend(
        id=1,
        name="Ana Silva",
        phone="11999",
        birthday=date(1990, 3, 15),
        category=Category.REKINDLE,
        cadence=Cadence.MONTHLY,
        notes=None,
    )
    # `tags` normalmente vem via relationship; usamos objetos FriendTag.
    f.tags = [FriendTag(friend_id=1, tag="rpg"), FriendTag(friend_id=1, tag="cerveja")]
    return f


def _make_interaction(note: str | None = "Falei com ele") -> Interaction:
    return Interaction(
        id=10,
        friend_id=1,
        occurred_at=datetime(2026, 4, 19, 14, 30, tzinfo=ZoneInfo(settings.timezone)),
        note=note,
        interaction_type=InteractionType.MESSAGE,
    )


def test_build_note_body_with_header_includes_metadata_block():
    body = evernote_service.build_note_body(
        _make_friend(), _make_interaction(), include_header=True
    )
    assert "Friends: Ana Silva" in body
    assert "Telefone: 11999 | Aniversario: 1990-03-15" in body
    assert "Categoria: rekindle | Cadencia: monthly" in body
    assert "Tags: cerveja, rpg" in body  # sorted
    assert "---" in body
    assert "[2026-04-19 14:30] message" in body
    assert "Falei com ele" in body


def test_build_note_body_without_header_is_just_entry():
    body = evernote_service.build_note_body(
        _make_friend(), _make_interaction(), include_header=False
    )
    assert body.startswith("[2026-04-19 14:30] message")
    assert "Friends: Ana Silva" not in body
    assert "---" not in body


def test_build_note_body_without_note_omits_empty_line():
    body = evernote_service.build_note_body(
        _make_friend(), _make_interaction(note=None), include_header=False
    )
    assert body == "[2026-04-19 14:30] message"


def test_build_note_title_uses_convention():
    assert evernote_service.build_note_title(_make_friend()) == "Friends: Ana Silva"


# ── sync service — sucesso, falha, cabecalho ─────────────────────


async def _seed(session) -> tuple[Friend, Interaction]:
    friend = Friend(
        name="Ana Silva",
        phone="11999",
        birthday=date(1990, 3, 15),
        category=Category.REKINDLE,
        cadence=Cadence.MONTHLY,
    )
    session.add(friend)
    await session.flush()
    session.add(FriendTag(friend_id=friend.id, tag="rpg"))
    inter = Interaction(
        friend_id=friend.id,
        occurred_at=datetime(2026, 4, 19, 14, 30, tzinfo=ZoneInfo(settings.timezone)),
        note="Falei com ele",
        interaction_type=InteractionType.MESSAGE,
    )
    session.add(inter)
    await session.flush()
    return friend, inter


def _success_transport() -> httpx.MockTransport:
    return httpx.MockTransport(lambda req: httpx.Response(200, text="Congratulations"))


def _failure_transport(status: int = 500) -> httpx.MockTransport:
    return httpx.MockTransport(lambda req: httpx.Response(status, text="boom"))


@pytest.mark.asyncio
async def test_sync_success_persists_sync_event_and_includes_header(session):
    # precisa de uma chave configurada para o client nao abortar
    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        friend, inter = await _seed(session)
        transport = _success_transport()
        async with httpx.AsyncClient(transport=transport) as http:
            result = await evernote_service.sync_interaction_to_evernote(
                session, friend.id, inter.id, http_client=http
            )
    assert result.status == SyncStatus.SUCCESS
    assert result.payload_json["include_header"] is True
    assert "Friends: Ana Silva" in result.payload_json["value2"]

    events = (await session.execute(select(SyncEvent))).scalars().all()
    assert len(events) == 1
    assert events[0].status == SyncStatus.SUCCESS
    assert events[0].entity_id == inter.id
    assert events[0].provider == SyncProvider.IFTTT


@pytest.mark.asyncio
async def test_sync_second_append_skips_header(session):
    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        friend, first = await _seed(session)
        transport = _success_transport()
        async with httpx.AsyncClient(transport=transport) as http:
            await evernote_service.sync_interaction_to_evernote(
                session, friend.id, first.id, http_client=http
            )

            # segunda interacao para o mesmo amigo
            second = Interaction(
                friend_id=friend.id,
                occurred_at=datetime(
                    2026, 4, 20, 9, 0, tzinfo=ZoneInfo(settings.timezone)
                ),
                note="Segundo contato",
                interaction_type=InteractionType.CALL,
            )
            session.add(second)
            await session.flush()

            result = await evernote_service.sync_interaction_to_evernote(
                session, friend.id, second.id, http_client=http
            )
    assert result.payload_json["include_header"] is False
    assert "Friends: Ana Silva" not in result.payload_json["value2"]
    assert result.payload_json["value2"].startswith("[2026-04-20 09:00] call")


@pytest.mark.asyncio
async def test_sync_webhook_failure_persists_failed_event_and_propagates(
    session_factory,
):
    # usa session_factory porque a `session` fixture compartilha a mesma
    # sessao do teste, e o commit interno do servico em caso de falha
    # fecharia objetos ainda em uso.
    from app.database import Base, get_db  # noqa: F401 — schema ja criada
    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        async with session_factory() as s:
            friend, inter = await _seed(s)
            await s.commit()

        # segunda sessao pra o sync — simula uma request HTTP separada
        async with session_factory() as s:
            transport = _failure_transport(500)
            async with httpx.AsyncClient(transport=transport) as http:
                with pytest.raises(ifttt_client.IftttWebhookError):
                    await evernote_service.sync_interaction_to_evernote(
                        s, friend.id, inter.id, http_client=http
                    )

        # log deve sobreviver mesmo com a excecao tendo propagado
        async with session_factory() as s:
            events = (await s.execute(select(SyncEvent))).scalars().all()
            assert len(events) == 1
            assert events[0].status == SyncStatus.FAILED
            assert events[0].error_message is not None
            assert "500" in events[0].error_message


@pytest.mark.asyncio
async def test_sync_unknown_friend_raises_404(session):
    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        transport = _success_transport()
        async with httpx.AsyncClient(transport=transport) as http:
            with pytest.raises(Exception) as excinfo:
                await evernote_service.sync_interaction_to_evernote(
                    session, 999, 1, http_client=http
                )
    assert "friend" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_sync_interaction_of_other_friend_raises_404(session):
    friend_a = Friend(name="Ana", category=Category.REKINDLE, cadence=Cadence.MONTHLY)
    friend_b = Friend(name="Bruno", category=Category.UPGRADE, cadence=Cadence.WEEKLY)
    session.add_all([friend_a, friend_b])
    await session.flush()
    inter = Interaction(
        friend_id=friend_b.id,
        occurred_at=datetime.now(tz=ZoneInfo(settings.timezone)),
        interaction_type=InteractionType.MESSAGE,
    )
    session.add(inter)
    await session.flush()

    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        transport = _success_transport()
        async with httpx.AsyncClient(transport=transport) as http:
            with pytest.raises(Exception) as excinfo:
                # inter pertence ao B; chamar com friend_a deve quebrar
                await evernote_service.sync_interaction_to_evernote(
                    session, friend_a.id, inter.id, http_client=http
                )
    assert "interaction" in str(excinfo.value).lower()


# ── Endpoint HTTP ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evernote_sync_endpoint_success(client, session_factory):
    # semeia um amigo + interacao diretamente no DB
    async with session_factory() as s:
        friend, inter = await _seed(s)
        await s.commit()
        friend_id, inter_id = friend.id, inter.id

    # mocka `ifttt_client.trigger_webhook` para nao bater na rede real
    with (
        patch.object(settings, "ifttt_webhook_key", "testkey"),
        patch.object(
            ifttt_client, "trigger_webhook", new=AsyncMock(return_value="ok")
        ),
    ):
        response = await client.post(
            f"/api/integrations/evernote/friends/{friend_id}/sync",
            json={"interaction_id": inter_id},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "ifttt"
    assert body["status"] == "success"
    assert body["entity_id"] == inter_id
    assert "Friends: Ana Silva" in body["payload_json"]["value2"]


@pytest.mark.asyncio
async def test_evernote_sync_endpoint_returns_502_on_webhook_failure(
    client, session_factory
):
    async with session_factory() as s:
        friend, inter = await _seed(s)
        await s.commit()
        friend_id, inter_id = friend.id, inter.id

    async def boom(*args, **kwargs):
        raise ifttt_client.IftttWebhookError("IFTTT devolveu HTTP 500", status=500)

    with (
        patch.object(settings, "ifttt_webhook_key", "testkey"),
        patch.object(ifttt_client, "trigger_webhook", new=AsyncMock(side_effect=boom)),
    ):
        response = await client.post(
            f"/api/integrations/evernote/friends/{friend_id}/sync",
            json={"interaction_id": inter_id},
        )

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "IFTTT_WEBHOOK_FAILED"

    # log FAILED deve ter sobrevivido
    async with session_factory() as s:
        events = (await s.execute(select(SyncEvent))).scalars().all()
        assert len(events) == 1
        assert events[0].status == SyncStatus.FAILED


@pytest.mark.asyncio
async def test_evernote_sync_endpoint_unknown_friend_returns_404(client):
    with patch.object(settings, "ifttt_webhook_key", "testkey"):
        response = await client.post(
            "/api/integrations/evernote/friends/999/sync",
            json={"interaction_id": 1},
        )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_evernote_sync_endpoint_missing_config_returns_503(
    client, session_factory
):
    async with session_factory() as s:
        friend, inter = await _seed(s)
        await s.commit()
        friend_id, inter_id = friend.id, inter.id

    with patch.object(settings, "ifttt_webhook_key", ""):
        response = await client.post(
            f"/api/integrations/evernote/friends/{friend_id}/sync",
            json={"interaction_id": inter_id},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "IFTTT_NOT_CONFIGURED"
