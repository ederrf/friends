"""Cliente HTTP para webhooks do IFTTT.

A integracao com Evernote (PRD §11) e feita via applet IFTTT do tipo
`Webhooks (Receive a web request) -> Evernote (Append to note)`. O
backend so fala com IFTTT; o Evernote e invisivel para o codigo.

API publica do Maker:
    POST https://maker.ifttt.com/trigger/{event}/with/key/{key}
    body JSON: {"value1": "...", "value2": "...", "value3": "..."}

Sucesso devolve 200 com "Congratulations! ...". Falhas retornam 401
(chave invalida), 404 (evento nao configurado) ou 5xx.

Esta camada e puramente adaptador HTTP. A decisao de o que enviar e dos
servicos de dominio que a chamam (`evernote_service`, futuramente
outros triggers).
"""

from __future__ import annotations

import httpx

from app.config import settings
from app.errors import AppError

_MAKER_URL = "https://maker.ifttt.com/trigger/{event}/with/key/{key}"
_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class IftttConfigError(AppError):
    """Configuracao faltando (chave ou evento)."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code="IFTTT_NOT_CONFIGURED",
            message=message,
            status_code=503,
        )


class IftttWebhookError(AppError):
    """Falha ao disparar o webhook (rede ou status HTTP >= 400)."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(
            code="IFTTT_WEBHOOK_FAILED",
            message=message,
            status_code=502,
            details={"provider_status": status} if status is not None else {},
        )


async def trigger_webhook(
    value1: str,
    value2: str | None = None,
    value3: str | None = None,
    *,
    event: str | None = None,
    key: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Dispara o webhook configurado e devolve o corpo da resposta.

    Parametros `event` e `key` aceitam override para testes; sem eles,
    usa `settings.ifttt_event_name` e `settings.ifttt_webhook_key`.

    `client` opcional permite injetar um `AsyncClient` em testes
    (httpx.MockTransport) sem monkey-patch global.
    """
    event_name = event or settings.ifttt_event_name
    webhook_key = key if key is not None else settings.ifttt_webhook_key

    if not webhook_key:
        raise IftttConfigError(
            "IFTTT_WEBHOOK_KEY nao configurado. Veja backend/.env.example."
        )
    if not event_name:
        raise IftttConfigError("IFTTT_EVENT_NAME nao configurado.")

    url = _MAKER_URL.format(event=event_name, key=webhook_key)
    payload: dict[str, str] = {"value1": value1}
    if value2 is not None:
        payload["value2"] = value2
    if value3 is not None:
        payload["value3"] = value3

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.post(url, json=payload)

    try:
        if client is not None:
            response = await _do(client)
        else:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
                response = await _do(c)
    except httpx.HTTPError as exc:
        raise IftttWebhookError(f"Falha de rede ao chamar IFTTT: {exc}") from exc

    if response.status_code >= 400:
        raise IftttWebhookError(
            f"IFTTT devolveu HTTP {response.status_code}: {response.text[:200]}",
            status=response.status_code,
        )
    return response.text
