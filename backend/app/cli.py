"""CLI sederhana: `python -m app.cli seed` / `python -m app.cli init-db`."""

from __future__ import annotations

import asyncio
import sys

from app.db import SessionLocal, engine
from app.factors.seed import seed
from app.models import Base


async def _init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabel dibuat (create_all).")


async def _seed() -> None:
    await _init_db()
    async with SessionLocal() as session:
        report = await seed(session)
    print("Seed selesai:", report)


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "seed"
    if cmd == "init-db":
        asyncio.run(_init_db())
    elif cmd == "seed":
        asyncio.run(_seed())
    else:
        print(f"Perintah tidak dikenal: {cmd}. Gunakan: init-db | seed")
        sys.exit(1)


if __name__ == "__main__":
    main()
