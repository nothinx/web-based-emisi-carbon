"""Test domain Organizational: mapping multi-fasilitas, rollup Scope 1/2/3,
faktor grid regional per fasilitas, reproducibility, & HTTP calculate."""

from __future__ import annotations

import pytest

from app.domains.organizational import OrganizationalDomain


def test_to_activities_multifacility_and_org_level():
    dom = OrganizationalDomain()
    specs = dom.to_activities(
        {
            "facilities": [
                {"name": "Pabrik A", "region": "ID-Jamali",
                 "electricity_kwh": 100000, "diesel_stationary_l": 0},
                {"name": "Pabrik B", "region": "ID-Sumatera",
                 "electricity_kwh": 50000, "lpg_kg": 200},
            ],
            "business_travel_air_pkm": 50000,
            "waste_landfill_kg": 0,  # nol dilewati
        }
    )
    # 2 listrik + 1 lpg + 1 business travel = 4 (diesel 0 & waste 0 dilewati).
    assert len(specs) == 4
    elec = [s for s in specs if s.category_code == "elec_grid"]
    assert {s.domain_fields["region"] for s in elec} == {"ID-Jamali", "ID-Sumatera"}
    assert {s.domain_fields["facility"] for s in elec} == {"Pabrik A", "Pabrik B"}
    travel = [s for s in specs if s.category_code == "business_travel_air"][0]
    assert travel.domain_fields["facility"] == "Organisasi (lintas-fasilitas)"


async def _auth(client) -> dict:
    await client.post("/auth/register", json={"email": "org@uji.id", "password": "rahasia123"})
    tok = await client.post("/auth/token", data={"username": "org@uji.id", "password": "rahasia123"})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.mark.asyncio
async def test_schema_endpoint_has_facilities(client):
    r = await client.get("/domains/organizational/schema")
    assert r.status_code == 200
    schema = r.json()["input_schema"]
    assert schema["properties"]["facilities"]["type"] == "array"
    assert "electricity_kwh" in schema["properties"]["facilities"]["items"]["properties"]


@pytest.mark.asyncio
async def test_domains_list_includes_org(client):
    r = await client.get("/domains")
    ids = {d["domain_id"] for d in r.json()}
    assert {"personal", "organizational"} <= ids


@pytest.mark.asyncio
async def test_calculate_org_scope_and_facility_rollup(client):
    headers = await _auth(client)
    payload = {
        "gwp_set_name": "AR6",
        "base_year": 2024,
        "inputs": {
            "facilities": [
                {"name": "Pabrik A", "region": "ID-Jamali", "electricity_kwh": 100000},
                {"name": "Pabrik B", "region": "ID-Sumatera",
                 "electricity_kwh": 100000, "diesel_stationary_l": 1000},
            ],
            "business_travel_air_pkm": 50000,
        },
    }
    r = await client.post("/domains/organizational/calculate", headers=headers, json=payload)
    assert r.status_code == 200
    report = r.json()["report"]

    # Grid regional: Jamali 0.87 vs Sumatera 1.18 (faktor berbeda per fasilitas).
    scope2 = 100000 * 0.87 + 100000 * 1.18
    scope1 = 1000 * 2.66155                  # diesel stasioner
    scope3 = 50000 * 0.158                   # perjalanan dinas udara
    assert report["total_co2e_kg"] == pytest.approx(scope1 + scope2 + scope3)

    rollup = {s["scope"]: s["co2e_kg"] for s in report["scope_rollup"]}
    assert rollup[1] == pytest.approx(scope1)
    assert rollup[2] == pytest.approx(scope2)
    assert rollup[3] == pytest.approx(scope3)
    assert sum(s["share"] for s in report["scope_rollup"]) == pytest.approx(1.0)

    # Facility rollup: Pabrik B (listrik Sumatera + diesel) > Pabrik A.
    facs = {f["name"]: f for f in report["facility_rollup"]}
    assert facs["Pabrik B"]["co2e_kg"] > facs["Pabrik A"]["co2e_kg"]
    assert facs["Pabrik A"]["co2e_kg"] == pytest.approx(100000 * 0.87)
    # Pabrik B punya rincian Scope 1 & Scope 2.
    b_scopes = {x["scope"] for x in facs["Pabrik B"]["by_scope"]}
    assert b_scopes == {1, 2}

    # Org tak pakai benchmark per-kapita.
    assert report["benchmarks"] is None
    # Ketidakpastian total hadir.
    assert report["uncertainty"]["ci_high"] > report["uncertainty"]["mean"]


@pytest.mark.asyncio
async def test_calculate_org_reproducible(client):
    headers = await _auth(client)
    payload = {
        "gwp_set_name": "AR6",
        "inputs": {"facilities": [{"name": "X", "region": "ID-Jamali", "electricity_kwh": 12345}]},
    }
    r1 = await client.post("/domains/organizational/calculate", headers=headers, json=payload)
    r2 = await client.post("/domains/organizational/calculate", headers=headers, json=payload)
    assert r1.json()["report"]["total_co2e_kg"] == pytest.approx(
        r2.json()["report"]["total_co2e_kg"]
    )
    assert r1.json()["run_id"] != r2.json()["run_id"]


@pytest.mark.asyncio
async def test_calculate_org_empty_422(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/organizational/calculate", headers=headers,
        json={"inputs": {"facilities": [{"name": "Kosong", "region": "GLOBAL"}]}},
    )
    assert r.status_code == 422
