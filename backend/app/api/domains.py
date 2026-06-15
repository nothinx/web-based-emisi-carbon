"""Router domain: schema form dinamis + kalkulasi domain (persist + reproducible)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.engine import run_calculation
from app.domains.registry import DOMAINS, get_domain
from app.models.project import ActivityRecord, CalculationRun, Project
from app.models.registry import Category, GWPSet

router = APIRouter(prefix="/domains", tags=["domains"])


class DomainCalcIn(BaseModel):
    name: str | None = None
    region: str = "GLOBAL"
    gwp_set_name: str = "AR6"
    inputs: dict = Field(default_factory=dict)


@router.get("")
async def list_domains():
    return [
        {"domain_id": d.domain_id, "title": d.input_schema.get("title", d.domain_id)}
        for d in DOMAINS.values()
    ]


@router.get("/{domain_id}/schema")
async def get_schema(domain_id: str):
    domain = get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' belum tersedia")
    return {"input_schema": domain.input_schema, "benchmarks": domain.benchmarks}


@router.post("/{domain_id}/calculate")
async def calculate_domain(
    domain_id: str, data: DomainCalcIn, session: SessionDep, user: CurrentUser
):
    domain = get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_id}' belum tersedia")

    gwp_set = (
        await session.execute(select(GWPSet).where(GWPSet.name == data.gwp_set_name))
    ).scalar_one_or_none()
    if gwp_set is None:
        raise HTTPException(status_code=400, detail=f"GWP set '{data.gwp_set_name}' tidak ada")

    specs = domain.to_activities(data.inputs)
    if not specs:
        raise HTTPException(status_code=422, detail="Tidak ada input yang bisa dihitung.")

    # Resolve kategori sekaligus.
    codes = {s.category_code for s in specs}
    cats = {
        c.code: c
        for c in (
            await session.execute(select(Category).where(Category.code.in_(codes)))
        ).scalars().all()
    }
    missing = codes - set(cats)
    if missing:
        raise HTTPException(status_code=400, detail=f"Kategori tak dikenal: {missing}")

    # Buat project + activities (persist agar reproducible).
    project = Project(
        owner_id=user.id,
        name=data.name or "Kalkulasi Personal",
        domain=domain_id,
        region=data.region,
        gwp_set_id=gwp_set.id,
    )
    session.add(project)
    await session.flush()

    for s in specs:
        session.add(
            ActivityRecord(
                project_id=project.id,
                category_id=cats[s.category_code].id,
                amount=s.amount,
                unit=s.unit,
                period=s.period,
                domain_fields=s.domain_fields,
                data_origin="manual",
            )
        )
    await session.flush()

    run = CalculationRun(
        project_id=project.id,
        created_at=datetime.now(timezone.utc),
        gwp_set_id=gwp_set.id,
        methodology_config={},
        uncertainty_method="analytical",
    )
    session.add(run)
    await session.flush()
    results = await run_calculation(session, run)
    await session.commit()

    report = domain.aggregate(results)
    return {
        "project_id": str(project.id),
        "run_id": str(run.id),
        "report": asdict(report),
    }
