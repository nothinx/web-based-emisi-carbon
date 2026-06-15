"""Engine, session, dan Base SQLAlchemy 2.x (async).

Desain Postgres-ready: tipe portable (Uuid, JSON->JSONB variant) dipakai di
`app/models/base.py`, sehingga ganti `DATABASE_URL` cukup untuk pindah ke Postgres.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# SQLite butuh check_same_thread=False saat dipakai lintas task async.
_connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_async_engine(
    settings.database_url,
    echo=settings.sql_echo,
    future=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)

if settings.is_sqlite:
    # SQLite tidak menegakkan foreign key secara default; aktifkan agar
    # constraint (self-FK Category, immutability via FK) berlaku seperti Postgres.
    @event.listens_for(engine.sync_engine, "connect")
    def _enable_sqlite_fk(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency FastAPI: satu session per request."""
    async with SessionLocal() as session:
        yield session
