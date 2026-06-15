"""Router ingestion: sensor/IoT -> ActivityRecord (data_origin=sensor).

Auth via API key terpisah (mesin), bukan JWT (user). Versi dasar fungsional;
batching & buffering real-time diperdalam di Phase 4.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep, require_ingestion_key
from app.models.enums import DataOrigin
from app.models.project import ActivityRecord, Project
from app.models.registry import Category
from app.schemas.project import ActivityOut

router = APIRouter(tags=["ingestion"], dependencies=[Depends(require_ingestion_key)])


class IngestIn(BaseModel):
    project_id: uuid.UUID
    category_code: str
    amount: float
    unit: str
    period: str | None = None
    domain_fields: dict = Field(default_factory=dict)
    sensor_id: str | None = None


def _to_activity(proj_id: uuid.UUID, cat_id: uuid.UUID, r: IngestIn) -> ActivityRecord:
    fields = dict(r.domain_fields)
    if r.sensor_id:
        fields["sensor_id"] = r.sensor_id
    return ActivityRecord(
        project_id=proj_id,
        category_id=cat_id,
        amount=r.amount,
        unit=r.unit,
        period=r.period,
        domain_fields=fields,
        data_origin=DataOrigin.sensor.value,
    )


async def _resolve(session, project_id: uuid.UUID, code: str):
    proj = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    cat = (
        await session.execute(select(Category).where(Category.code == code))
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail=f"Kategori '{code}' tidak ada")
    return proj, cat


@router.post("/ingest", response_model=ActivityOut, status_code=201)
async def ingest(data: IngestIn, session: SessionDep):
    proj, cat = await _resolve(session, data.project_id, data.category_code)
    act = _to_activity(proj.id, cat.id, data)
    session.add(act)
    await session.commit()
    return act


class IngestBatchIn(BaseModel):
    readings: list[IngestIn] = Field(..., min_length=1, max_length=5000)


@router.post("/ingest/batch", status_code=201)
async def ingest_batch(data: IngestBatchIn, session: SessionDep):
    """Batch sensor → ActivityRecord (stream/buffer IoT). Resolusi project+kategori
    di-cache per batch agar efisien. Semua atau gagal (satu transaksi)."""
    cache: dict[tuple, tuple] = {}
    created = 0
    for r in data.readings:
        key = (r.project_id, r.category_code)
        if key not in cache:
            cache[key] = await _resolve(session, r.project_id, r.category_code)
        proj, cat = cache[key]
        session.add(_to_activity(proj.id, cat.id, r))
        created += 1
    await session.commit()
    return {"ingested": created, "sensors": sorted({r.sensor_id for r in data.readings if r.sensor_id})}
