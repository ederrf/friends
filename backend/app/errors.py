"""Formato de erro padrao da API (PRD secao 9.7).

Toda resposta de erro segue:

    {"error": {"code": "STRING_CODE", "message": "...", "details": {...}}}

`AppError` e a excecao canonica do dominio. HTTPException do FastAPI e
ValidationError do Pydantic sao convertidas para o mesmo formato via
handlers registrados em `app.main`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Erro de dominio com codigo, status HTTP e detalhes estruturados."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


# ── Erros canonicos reutilizaveis ───────────────────────────────


class NotFoundError(AppError):
    def __init__(self, entity: str, entity_id: int | str) -> None:
        super().__init__(
            code=f"{entity.upper()}_NOT_FOUND",
            message=f"{entity} {entity_id} nao encontrado.",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"entity": entity, "id": entity_id},
        )


class ConflictError(AppError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class ExternalServiceError(AppError):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(
            code=code,
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details,
        )


# ── Handlers ────────────────────────────────────────────────────


def _error_payload(code: str, message: str, details: dict[str, Any] | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or {}}}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(exc.code, exc.message, exc.details),
    )


async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    # Mapeia HTTPException padrao do FastAPI para o formato do PRD.
    code = {
        status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
        status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
        status.HTTP_403_FORBIDDEN: "FORBIDDEN",
        status.HTTP_404_NOT_FOUND: "NOT_FOUND",
        status.HTTP_409_CONFLICT: "CONFLICT",
        status.HTTP_422_UNPROCESSABLE_ENTITY: "UNPROCESSABLE_ENTITY",
    }.get(exc.status_code, "HTTP_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "Erro HTTP."
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(code, message),
    )


async def validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=_error_payload(
            code="VALIDATION_ERROR",
            message="Payload invalido.",
            details={"errors": jsonable_encoder(exc.errors())},
        ),
    )


async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_error_payload(
            code="INTERNAL_ERROR",
            message="Erro interno nao esperado.",
            details={"type": exc.__class__.__name__},
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra todos os handlers no app FastAPI."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
