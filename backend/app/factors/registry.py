"""Service Factor Registry: create & versioning.

Aturan: edit faktor = baris versi baru. Versi lama ditutup (`valid_to`, `is_active=False`),
baris baru `is_active=True`. TIDAK PERNAH UPDATE in-place pada nilai faktor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.registry import EmissionFactor
from app.schemas.registry import EmissionFactorIn


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _current_active(
    session: AsyncSession, category_id: uuid.UUID, gas_id: uuid.UUID, region: str
) -> EmissionFactor | None:
    return (
        await session.execute(
            select(EmissionFactor).where(
                EmissionFactor.category_id == category_id,
                EmissionFactor.gas_id == gas_id,
                EmissionFactor.region == region,
                EmissionFactor.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()


async def create_factor(session: AsyncSession, data: EmissionFactorIn) -> EmissionFactor:
    """Buat faktor. Jika sudah ada versi aktif untuk (kategori,gas,region), tutup dulu."""
    now = _now()
    prev = await _current_active(session, data.category_id, data.gas_id, data.region)
    version = 1
    if prev is not None:
        prev.is_active = False
        prev.valid_to = now
        version = prev.version + 1

    factor = EmissionFactor(
        category_id=data.category_id,
        gas_id=data.gas_id,
        source_id=data.source_id,
        value=data.value,
        unit=data.unit,
        region=data.region,
        gwp_basis=data.gwp_basis,
        tier=data.tier,
        version=version,
        valid_from=data.valid_from or now,
        valid_to=None,
        is_active=True,
        dist_type=data.dist_type.value if data.dist_type else None,
        dist_params=data.dist_params,
        uncertainty_pct=data.uncertainty_pct,
        meta=data.meta,
    )
    session.add(factor)
    await session.flush()
    return factor


async def new_version(
    session: AsyncSession, factor_id: uuid.UUID, data: EmissionFactorIn
) -> EmissionFactor:
    """Buat versi baru menggantikan faktor `factor_id` (yang ditutup)."""
    current = (
        await session.execute(select(EmissionFactor).where(EmissionFactor.id == factor_id))
    ).scalar_one()
    # Paksa konteks identitas faktor tetap sama (kategori/gas/region).
    data = data.model_copy(
        update={
            "category_id": current.category_id,
            "gas_id": current.gas_id,
            "region": current.region,
        }
    )
    return await create_factor(session, data)


async def list_active(
    session: AsyncSession,
    *,
    category_id: uuid.UUID | None = None,
    region: str | None = None,
) -> list[EmissionFactor]:
    stmt = (
        select(EmissionFactor)
        .where(EmissionFactor.is_active.is_(True))
        .options(
            selectinload(EmissionFactor.gas),
            selectinload(EmissionFactor.source),
            selectinload(EmissionFactor.category),
        )
        .order_by(EmissionFactor.created_at.desc())
    )
    if category_id:
        stmt = stmt.where(EmissionFactor.category_id == category_id)
    if region:
        stmt = stmt.where(EmissionFactor.region == region)
    return list((await session.execute(stmt)).scalars().all())


async def versions_of(
    session: AsyncSession, factor_id: uuid.UUID
) -> list[EmissionFactor]:
    """Seluruh riwayat versi untuk identitas (kategori,gas,region) dari faktor ini."""
    anchor = (
        await session.execute(select(EmissionFactor).where(EmissionFactor.id == factor_id))
    ).scalar_one()
    return list(
        (
            await session.execute(
                select(EmissionFactor)
                .where(
                    EmissionFactor.category_id == anchor.category_id,
                    EmissionFactor.gas_id == anchor.gas_id,
                    EmissionFactor.region == anchor.region,
                )
                .options(selectinload(EmissionFactor.source))
                .order_by(EmissionFactor.version.asc())
            )
        )
        .scalars()
        .all()
    )
