"""Router Project: CRUD project & activity, jalankan kalkulasi, ambil hasil immutable."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, SessionDep
from app.core.engine import run_calculation
from app.models.project import (
    ActivityRecord,
    CalculationRun,
    Project,
    Scenario,
)
from app.schemas.project import (
    ActivityIn,
    ActivityOut,
    ProjectIn,
    ProjectOut,
    ResultOut,
    RunDetailOut,
    RunIn,
    RunOut,
    ScenarioIn,
    ScenarioOut,
)

router = APIRouter(tags=["projects"])


async def _get_project(session, project_id: uuid.UUID) -> Project:
    proj = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if proj is None:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan")
    return proj


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(data: ProjectIn, session: SessionDep, user: CurrentUser):
    proj = Project(owner_id=user.id, **data.model_dump())
    session.add(proj)
    await session.commit()
    return proj


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(session: SessionDep, user: CurrentUser):
    rows = (
        await session.execute(select(Project).where(Project.owner_id == user.id))
    ).scalars().all()
    return list(rows)


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: uuid.UUID, session: SessionDep, _: CurrentUser):
    return await _get_project(session, project_id)


# --- Activities ---
@router.post("/projects/{project_id}/activities", response_model=ActivityOut, status_code=201)
async def add_activity(
    project_id: uuid.UUID, data: ActivityIn, session: SessionDep, _: CurrentUser
):
    await _get_project(session, project_id)
    act = ActivityRecord(
        project_id=project_id,
        category_id=data.category_id,
        amount=data.amount,
        unit=data.unit,
        period=data.period,
        domain_fields=data.domain_fields,
        data_origin=data.data_origin.value,
        activity_uncertainty=data.activity_uncertainty,
    )
    session.add(act)
    await session.commit()
    return act


@router.get("/projects/{project_id}/activities", response_model=list[ActivityOut])
async def list_activities(project_id: uuid.UUID, session: SessionDep, _: CurrentUser):
    rows = (
        await session.execute(
            select(ActivityRecord).where(ActivityRecord.project_id == project_id)
        )
    ).scalars().all()
    return list(rows)


# --- Calculate ---
@router.post("/projects/{project_id}/calculate", response_model=RunDetailOut, status_code=201)
async def calculate(
    project_id: uuid.UUID, data: RunIn, session: SessionDep, _: CurrentUser
):
    proj = await _get_project(session, project_id)
    run = CalculationRun(
        project_id=proj.id,
        created_at=datetime.now(timezone.utc),
        gwp_set_id=data.gwp_set_id or proj.gwp_set_id,
        methodology_config=data.methodology_config,
        uncertainty_method=data.uncertainty_method.value,
    )
    session.add(run)
    await session.flush()
    results = await run_calculation(session, run)
    await session.commit()

    total = sum(r.co2e_kg for r in results)
    return RunDetailOut(
        id=run.id,
        project_id=run.project_id,
        created_at=run.created_at,
        gwp_set_id=run.gwp_set_id,
        methodology_config=run.methodology_config,
        uncertainty_method=run.uncertainty_method,
        status=run.status,
        results=[ResultOut.model_validate(r) for r in results],
        total_co2e_kg=total,
    )


# --- Runs & results (immutable) ---
@router.get("/projects/{project_id}/runs", response_model=list[RunOut])
async def list_runs(project_id: uuid.UUID, session: SessionDep, _: CurrentUser):
    rows = (
        await session.execute(
            select(CalculationRun)
            .where(CalculationRun.project_id == project_id)
            .order_by(CalculationRun.created_at.desc())
        )
    ).scalars().all()
    return list(rows)


@router.get("/runs/{run_id}/results", response_model=RunDetailOut)
async def get_run_results(run_id: uuid.UUID, session: SessionDep, _: CurrentUser):
    run = (
        await session.execute(
            select(CalculationRun)
            .where(CalculationRun.id == run_id)
            .options(selectinload(CalculationRun.results))
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run tidak ditemukan")
    total = sum(r.co2e_kg for r in run.results)
    return RunDetailOut(
        id=run.id,
        project_id=run.project_id,
        created_at=run.created_at,
        gwp_set_id=run.gwp_set_id,
        methodology_config=run.methodology_config,
        uncertainty_method=run.uncertainty_method,
        status=run.status,
        results=[ResultOut.model_validate(r) for r in run.results],
        total_co2e_kg=total,
    )


# --- Scenarios (what-if; eksekusi penuh di Phase 3) ---
@router.post("/projects/{project_id}/scenarios", response_model=ScenarioOut, status_code=201)
async def create_scenario(
    project_id: uuid.UUID, data: ScenarioIn, session: SessionDep, _: CurrentUser
):
    await _get_project(session, project_id)
    sc = Scenario(project_id=project_id, name=data.name, overrides=data.overrides)
    session.add(sc)
    await session.commit()
    return sc


@router.post("/projects/{project_id}/scenarios/{scenario_id}/run")
async def run_scenario(
    project_id: uuid.UUID, scenario_id: uuid.UUID, session: SessionDep, _: CurrentUser
):
    """Jalankan what-if: hitung baseline lalu terapkan override skala per-kategori.

    `overrides`: `{"factor_scale": {kode: x}, "activity_scale": {kode: y}}` — keduanya
    mengali kontribusi co2e kategori (co2e = aktivitas × faktor, jadi keduanya
    multiplikatif). Mengembalikan perbandingan baseline vs skenario + delta per kategori.
    Baseline dihitung dari run baru (immutable, reproducible); skenario adalah proyeksi
    analitis di atas baseline (tak menyentuh faktor live).
    """
    proj = await _get_project(session, project_id)
    sc = (
        await session.execute(
            select(Scenario).where(
                Scenario.id == scenario_id, Scenario.project_id == project_id
            )
        )
    ).scalar_one_or_none()
    if sc is None:
        raise HTTPException(status_code=404, detail="Scenario tidak ditemukan")

    run = CalculationRun(
        project_id=proj.id,
        created_at=datetime.now(timezone.utc),
        gwp_set_id=proj.gwp_set_id,
        methodology_config={"scenario_id": str(sc.id)},
        uncertainty_method="analytical",
    )
    session.add(run)
    await session.flush()
    results = await run_calculation(session, run)
    await session.commit()

    overrides = sc.overrides or {}
    fscale = overrides.get("factor_scale", {})
    ascale = overrides.get("activity_scale", {})

    base_cat: dict[str, dict] = {}
    for r in results:
        cat = r.factor_snapshot.get("category", {})
        code = cat.get("code", "lain")
        g = base_cat.setdefault(code, {"category": code, "name": cat.get("name", code), "baseline": 0.0})
        g["baseline"] += r.co2e_kg

    by_category = []
    base_total = 0.0
    scen_total = 0.0
    for code, g in base_cat.items():
        scale = float(fscale.get(code, 1.0)) * float(ascale.get(code, 1.0))
        scen = g["baseline"] * scale
        base_total += g["baseline"]
        scen_total += scen
        by_category.append({
            "category": code, "name": g["name"], "scale": scale,
            "baseline_kg": g["baseline"], "scenario_kg": scen,
            "delta_kg": scen - g["baseline"],
        })
    by_category.sort(key=lambda x: abs(x["delta_kg"]), reverse=True)

    return {
        "scenario_id": str(sc.id),
        "name": sc.name,
        "run_id": str(run.id),
        "baseline_total_kg": base_total,
        "scenario_total_kg": scen_total,
        "delta_kg": scen_total - base_total,
        "delta_pct": ((scen_total - base_total) / base_total * 100.0) if base_total else 0.0,
        "by_category": by_category,
    }
