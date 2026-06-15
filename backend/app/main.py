"""Entry FastAPI: app factory, CORS, lifespan (dev create_all + seed), routers."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, domains, factors, ingest, projects
from app.config import settings
from app.db import SessionLocal, engine
from app.factors.seed import seed
from app.models import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Dev (SQLite): buat tabel dari metadata + seed faktor contoh.
    # Prod (Postgres): gunakan `alembic upgrade head`; create_all tetap aman/idempoten.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed(session)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Carbon Emission Engine",
        version="0.1.0",
        description="Research-grade multi-domain carbon emission calculator (Phase 0).",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router)
    app.include_router(factors.router)
    app.include_router(projects.router)
    app.include_router(domains.router)
    app.include_router(ingest.router)

    @app.get("/health", tags=["meta"])
    async def health():
        return {"status": "ok", "db": "sqlite" if settings.is_sqlite else "postgres"}

    return app


app = create_app()
