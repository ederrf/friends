"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    All values can be overridden via environment variables or .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────
    app_name: str = "Friends"
    debug: bool = False
    timezone: str = "America/Sao_Paulo"

    # ── Database ─────────────────────────────────────────────────
    # SQLite local-first para v1.
    database_url: str = "sqlite+aiosqlite:///./friends.db"

    # ── Frontend ─────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # ── Integracao Evernote via IFTTT ────────────────────────────
    # Chave do webhook do IFTTT (https://ifttt.com/maker_webhooks/settings)
    ifttt_webhook_key: str = ""
    # Nome do evento configurado no applet `Webhooks -> Evernote Append to note`.
    ifttt_event_name: str = "friends_log"

    # ── Integracao Google Calendar ───────────────────────────────
    google_client_id: str = ""
    google_client_secret: str = ""
    # Caminho onde o refresh_token do usuario e persistido (fora do repo).
    google_token_path: str = "~/.friends/google_token.json"


settings = Settings()
