"""Fixtures pytest. DB uji = file SQLite terpisah, dibuat & di-seed sekali."""

from __future__ import annotations

import os
import pathlib

# Set DB uji SEBELUM import apa pun dari app (engine dibuat saat import).
_TEST_DB = pathlib.Path(__file__).resolve().parent / "test_carbon.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB.as_posix()}"
os.environ["JWT_SECRET"] = "test-secret"

if _TEST_DB.exists():
    _TEST_DB.unlink()

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.factors.seed import seed  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402

_prepared = False


@pytest_asyncio.fixture(autouse=True)
async def _prepare_db():
    """Buat tabel + seed sekali (idempoten)."""
    global _prepared
    if not _prepared:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with SessionLocal() as s:
            await seed(s)
        _prepared = True
    yield


@pytest_asyncio.fixture
async def session():
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def client():
    # ASGITransport tidak menjalankan lifespan; DB sudah disiapkan fixture di atas.
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
