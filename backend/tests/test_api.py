"""Test API end-to-end (HTTP): auth -> project -> activity -> calculate -> results."""

from __future__ import annotations

import pytest


async def _auth_headers(client) -> dict:
    await client.post("/auth/register", json={
        "email": "peneliti@example.com", "password": "rahasia123", "full_name": "Peneliti",
    })
    tok = await client.post("/auth/token", data={
        "username": "peneliti@example.com", "password": "rahasia123",
    })
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_factors_seeded(client):
    r = await client.get("/factors")
    assert r.status_code == 200
    assert len(r.json()) >= 10  # ~14 faktor contoh


@pytest.mark.asyncio
async def test_full_flow(client):
    headers = await _auth_headers(client)

    gwp_sets = (await client.get("/gwp-sets")).json()
    ar6 = next(g for g in gwp_sets if g["name"] == "AR6")
    cats = (await client.get("/categories?domain=personal")).json()
    elec = next(c for c in cats if c["code"] == "elec_grid")

    proj = await client.post("/projects", headers=headers, json={
        "name": "Rumah HTTP", "domain": "personal", "region": "ID-Jamali",
        "gwp_set_id": ar6["id"],
    })
    assert proj.status_code == 201
    pid = proj.json()["id"]

    act = await client.post(f"/projects/{pid}/activities", headers=headers, json={
        "category_id": elec["id"], "amount": 250, "unit": "kWh",
    })
    assert act.status_code == 201

    run = await client.post(f"/projects/{pid}/calculate", headers=headers, json={})
    assert run.status_code == 201
    body = run.json()
    assert body["status"] == "completed"
    assert body["total_co2e_kg"] == pytest.approx(250 * 0.87)
    assert body["results"][0]["factor_snapshot"]["source"]["name"]

    # Ambil ulang hasil immutable.
    rid = body["id"]
    again = await client.get(f"/runs/{rid}/results", headers=headers)
    assert again.json()["total_co2e_kg"] == pytest.approx(body["total_co2e_kg"])


@pytest.mark.asyncio
async def test_write_requires_auth(client):
    r = await client.post("/projects", json={
        "name": "x", "domain": "personal", "gwp_set_id": "00000000-0000-0000-0000-000000000000",
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_ingest_requires_api_key(client):
    r = await client.post("/ingest", json={
        "project_id": "00000000-0000-0000-0000-000000000000",
        "category_code": "elec_grid", "amount": 1, "unit": "kWh",
    })
    assert r.status_code == 401
