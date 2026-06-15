"""Test domain Personal: mapping input->aktivitas, agregasi, & HTTP calculate."""

from __future__ import annotations

import pytest

from app.domains.personal import PersonalDomain


def test_to_activities_annualizes():
    dom = PersonalDomain()
    specs = dom.to_activities({"electricity_kwh_month": 250, "beef_kg_week": 1, "car_km_year": 0})
    by_code = {s.category_code: s for s in specs}
    # listrik bulanan ×12, daging mingguan ×52, nilai 0 dilewati.
    assert by_code["elec_grid"].amount == pytest.approx(250 * 12)
    assert by_code["food_beef"].amount == pytest.approx(1 * 52)
    assert "car_petrol" not in by_code


async def _auth(client) -> dict:
    await client.post("/auth/register", json={"email": "p@uji.id", "password": "rahasia123"})
    tok = await client.post("/auth/token", data={"username": "p@uji.id", "password": "rahasia123"})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.mark.asyncio
async def test_schema_endpoint(client):
    r = await client.get("/domains/personal/schema")
    assert r.status_code == 200
    body = r.json()
    assert "electricity_kwh_month" in body["input_schema"]["properties"]
    assert body["benchmarks"]["values"]["world_avg"] > 0


@pytest.mark.asyncio
async def test_calculate_personal_flow(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/personal/calculate",
        headers=headers,
        json={
            "region": "ID-Jamali",
            "gwp_set_name": "AR6",
            "inputs": {"electricity_kwh_month": 250, "beef_kg_week": 1},
        },
    )
    assert r.status_code == 200
    report = r.json()["report"]
    # listrik: 250*12 kWh * 0.87 = 2610 kg; sapi: 52 kg * 99.48 = 5172.96 kg
    assert report["total_co2e_kg"] == pytest.approx(250 * 12 * 0.87 + 52 * 99.48)
    assert report["total_co2e_tonnes"] == pytest.approx(report["total_co2e_kg"] / 1000)
    assert len(report["breakdown"]) == 2
    # breakdown terurut menurun, share menjumlah ~1.
    assert report["breakdown"][0]["co2e_kg"] >= report["breakdown"][1]["co2e_kg"]
    assert sum(b["share"] for b in report["breakdown"]) == pytest.approx(1.0)
    # benchmark per kapita ada.
    assert "comparison" in report["benchmarks"]
    # ketidakpastian total hadir (sapi pakai lognormal).
    assert report["uncertainty"] is not None
    assert report["uncertainty"]["ci_high"] > report["uncertainty"]["mean"]


@pytest.mark.asyncio
async def test_calculate_empty_inputs_422(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/personal/calculate",
        headers=headers,
        json={"inputs": {}},
    )
    assert r.status_code == 422
