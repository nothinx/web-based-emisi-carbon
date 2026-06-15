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


@router.post("/ingest", response_model=ActivityOut, status_code=201)
async def ingest(data: IngestIn, session: SessionDep):
    proj = (
        await session.execute(select(Project).where(Project.id == data.project_id))
    ).scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    cat = (
        await session.execute(select(Category).where(Category.code == data.category_code))
    ).scalar_one_or_none()
    if cat is None:
        raise HTTPException(status_code=404, detail=f"Kategori '{data.category_code}' tidak ada")

    fields = dict(data.domain_fields)
    if data.sensor_id:
        fields["sensor_id"] = data.sensor_id

    act = ActivityRecord(
        project_id=proj.id,
        category_id=cat.id,
        amount=data.amount,
        unit=data.unit,
        period=data.period,
        domain_fields=fields,
        data_origin=DataOrigin.sensor.value,
    )
    session.add(act)
    await session.commit()
    return act
