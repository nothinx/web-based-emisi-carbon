"""Konfigurasi aplikasi (12-factor: dari environment)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database. Default SQLite async untuk dev; swap ke postgresql+asyncpg untuk prod.
    database_url: str = "sqlite+aiosqlite:///./carbon.db"
    sql_echo: bool = False

    # Auth (JWT untuk user, API key terpisah untuk mesin/sensor).
    jwt_secret: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    ingestion_api_key: str = "dev-ingestion-key-change-me"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def sync_database_url(self) -> str:
        """URL sinkron untuk Alembic (lepas driver async)."""
        return (
            self.database_url.replace("+aiosqlite", "")
            .replace("+asyncpg", "+psycopg")
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
