"""Router Factor Registry: faktor (versioned), sumber, gas, GWP set, kategori."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.factors import registry
from app.models.registry import (
    Category,
    FactorSource,
    Gas,
    GWPSet,
)
from app.schemas.registry import (
    CategoryIn,
    CategoryOut,
    EmissionFactorIn,
    EmissionFactorOut,
    FactorSourceIn,
    FactorSourceOut,
    GasIn,
    GasOut,
    GWPSetOut,
)

router = APIRouter(tags=["factors"])


# --- Lookups (read terbuka; write butuh auth) ---
@router.get("/sources", response_model=list[FactorSourceOut])
async def list_sources(session: SessionDep):
    return list((await session.execute(select(FactorSource))).scalars().all())


@router.post("/sources", response_model=FactorSourceOut, status_code=201)
async def create_source(data: FactorSourceIn, session: SessionDep, _: CurrentUser):
    obj = FactorSource(**data.model_dump())
    session.add(obj)
    await session.commit()
    return obj


@router.get("/gases", response_model=list[GasOut])
async def list_gases(session: SessionDep):
    return list((await session.execute(select(Gas))).scalars().all())


@router.post("/gases", response_model=GasOut, status_code=201)
async def create_gas(data: GasIn, session: SessionDep, _: CurrentUser):
    obj = Gas(**data.model_dump())
    session.add(obj)
    await session.commit()
    return obj


@router.get("/gwp-sets", response_model=list[GWPSetOut])
async def list_gwp_sets(session: SessionDep):
    return list((await session.execute(select(GWPSet))).scalars().all())


@router.get("/categories", response_model=list[CategoryOut])
async def list_categories(
    session: SessionDep,
    domain: str | None = Query(default=None),
):
    rows = list((await session.execute(select(Category))).scalars().all())
    if domain:
        rows = [c for c in rows if domain in (c.domain_applicability or [])]
    return rows


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(data: CategoryIn, session: SessionDep, _: CurrentUser):
    obj = Category(**data.model_dump())
    session.add(obj)
    await session.commit()
    return obj


# --- Emission factors (versioned) ---
@router.get("/factors", response_model=list[EmissionFactorOut])
async def list_factors(
    session: SessionDep,
    category_id: uuid.UUID | None = Query(default=None),
    region: str | None = Query(default=None),
):
    return await registry.list_active(session, category_id=category_id, region=region)


@router.post("/factors", response_model=EmissionFactorOut, status_code=201)
async def create_factor(data: EmissionFactorIn, session: SessionDep, _: CurrentUser):
    factor = await registry.create_factor(session, data)
    await session.commit()
    await session.refresh(factor)
    return factor


@router.get("/factors/{factor_id}/versions", response_model=list[EmissionFactorOut])
async def factor_versions(factor_id: uuid.UUID, session: SessionDep):
    rows = await registry.versions_of(session, factor_id)
    if not rows:
        raise HTTPException(status_code=404, detail="Faktor tidak ditemukan")
    return rows


@router.post(
    "/factors/{factor_id}/versions",
    response_model=EmissionFactorOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_factor_version(
    factor_id: uuid.UUID, data: EmissionFactorIn, session: SessionDep, _: CurrentUser
):
    factor = await registry.new_version(session, factor_id, data)
    await session.commit()
    await session.refresh(factor)
    return factor
