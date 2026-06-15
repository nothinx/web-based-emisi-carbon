"""Phase 4 — Sector (IPCC tier: enterik CH₄, manure N₂O, pupuk, sawah) + IoT batch."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.engine import run_calculation
from app.models.project import ActivityRecord, CalculationRun, Project
from app.models.registry import Category, GWPSet

API_KEY = {"X-API-Key": "dev-ingestion-key-change-me"}


async def _auth(client) -> dict:
    await client.post("/auth/register", json={"email": "p4@uji.id", "password": "rahasia123"})
    tok = await client.post("/auth/token", data={"username": "p4@uji.id", "password": "rahasia123"})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.mark.asyncio
async def test_sector_ipcc_breakdown(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/sector/calculate", headers=headers,
        json={"gwp_set_name": "AR6", "inputs": {
            "cattle_head": 10, "fertilizer_n_kg": 100, "rice_area_ha": 2,
            "electricity_kwh": 1000, "diesel_l": 100,
        }},
    )
    assert r.status_code == 200
    report = r.json()["report"]
    bd = {b["code"]: b["co2e_kg"] for b in report["breakdown"]}

    # Enterik Tier 1: 10 ekor × 68 kgCH4 × 27.9 (GWP CH4 AR6)
    assert bd["enteric_cattle"] == pytest.approx(10 * 68 * 27.9)
    # Manure Tier 1: 10 × Nex60 × MS1 × EF3 0.005 × 44/28 × 273 (GWP N2O)
    assert bd["manure_cattle"] == pytest.approx(10 * 60 * 1.0 * 0.005 * (44 / 28) * 273)
    # Pupuk N2O: 100 kgN × 0.015714 kgN2O/kgN × 273
    assert bd["fert_synthetic_n"] == pytest.approx(100 * 0.015714 * 273)
    # Sawah CH4: 2 ha × 143 × 27.9
    assert bd["rice_cultivation"] == pytest.approx(2 * 143 * 27.9)
    # Energi reuse: listrik GLOBAL 0.475, solar GLOBAL 2.66155
    assert bd["elec_grid"] == pytest.approx(1000 * 0.475)
    assert bd["diesel_stationary"] == pytest.approx(100 * 2.66155)
    assert report["methodology"]
    # Catatan menyebut metode IPCC Tier.
    assert any("IPCC" in n for n in report["notes"])


@pytest.mark.asyncio
async def test_enteric_tier2_from_domain_fields(session):
    """Tier 2 enterik: EF dihitung dari gross energy & Ym (bukan default Tier 1)."""
    ar6 = (await session.execute(select(GWPSet).where(GWPSet.name == "AR6"))).scalar_one()
    cat = (await session.execute(select(Category).where(Category.code == "enteric_cattle"))).scalar_one()
    proj = Project(name="Peternakan", domain="sector", region="GLOBAL", gwp_set_id=ar6.id)
    session.add(proj)
    await session.flush()
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cat.id, amount=10, unit="head",
        domain_fields={"gross_energy_mj_per_day": 200, "methane_conversion_pct": 6.5},
        data_origin="manual",
    ))
    await session.commit()

    run = CalculationRun(
        project_id=proj.id, created_at=datetime.now(timezone.utc),
        gwp_set_id=ar6.id, methodology_config={}, uncertainty_method="analytical",
    )
    session.add(run)
    await session.flush()
    results = await run_calculation(session, run)
    await session.commit()

    r = results[0]
    assert r.strategy_used == "ipcc.enteric.v2"
    assert r.assumptions["tier"] == 2
    ef = 200 * (6.5 / 100) * 365 / 55.65
    assert r.assumptions["ef_kg_ch4_per_head_yr"] == pytest.approx(ef)
    assert r.co2e_kg == pytest.approx(10 * ef * 27.9)


@pytest.mark.asyncio
async def test_sector_reproducible(client):
    headers = await _auth(client)
    body = {"gwp_set_name": "AR6", "inputs": {"cattle_head": 25, "rice_area_ha": 5}}
    a = await client.post("/domains/sector/calculate", headers=headers, json=body)
    b = await client.post("/domains/sector/calculate", headers=headers, json=body)
    assert a.json()["report"]["total_co2e_kg"] == pytest.approx(b.json()["report"]["total_co2e_kg"])


@pytest.mark.asyncio
async def test_ingest_batch_sensor(client):
    headers = await _auth(client)
    # Project sektor sebagai target ingestion.
    calc = await client.post(
        "/domains/sector/calculate", headers=headers,
        json={"gwp_set_name": "AR6", "inputs": {"cattle_head": 1}},
    )
    project_id = calc.json()["project_id"]

    readings = {
        "readings": [
            {"project_id": project_id, "category_code": "elec_grid", "amount": 12.5,
             "unit": "kWh", "sensor_id": "meter-01", "period": "2024-06"},
            {"project_id": project_id, "category_code": "elec_grid", "amount": 9.1,
             "unit": "kWh", "sensor_id": "meter-01", "period": "2024-06"},
            {"project_id": project_id, "category_code": "diesel_stationary", "amount": 3.0,
             "unit": "L", "sensor_id": "pump-02"},
        ]
    }
    r = await client.post("/ingest/batch", headers=API_KEY, json=readings)
    assert r.status_code == 201
    body = r.json()
    assert body["ingested"] == 3
    assert body["sensors"] == ["meter-01", "pump-02"]


@pytest.mark.asyncio
async def test_ingest_batch_requires_api_key(client):
    r = await client.post("/ingest/batch", json={"readings": [
        {"project_id": "00000000-0000-0000-0000-000000000000",
         "category_code": "elec_grid", "amount": 1, "unit": "kWh"}
    ]})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_sector_in_domains_list(client):
    r = await client.get("/domains")
    assert "sector" in {d["domain_id"] for d in r.json()}
