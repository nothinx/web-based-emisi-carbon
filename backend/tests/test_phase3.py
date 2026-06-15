"""Phase 3 — Monte Carlo (reproducible), sensitivity, & scenario what-if."""

from __future__ import annotations

import pytest


async def _auth(client) -> dict:
    await client.post("/auth/register", json={"email": "p3@uji.id", "password": "rahasia123"})
    tok = await client.post("/auth/token", data={"username": "p3@uji.id", "password": "rahasia123"})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


async def _calc(client, headers, **extra):
    body = {
        "region": "ID-Jamali", "gwp_set_name": "AR6",
        "inputs": {"electricity_kwh_month": 250, "beef_kg_week": 1},
    }
    body.update(extra)
    r = await client.post("/domains/personal/calculate", headers=headers, json=body)
    assert r.status_code == 200
    return r.json()


@pytest.mark.asyncio
async def test_montecarlo_reproducible(client):
    headers = await _auth(client)
    a = await _calc(client, headers, uncertainty_method="montecarlo", mc_seed=42, mc_iterations=4000)
    b = await _calc(client, headers, uncertainty_method="montecarlo", mc_seed=42, mc_iterations=4000)
    mca, mcb = a["report"]["mc"], b["report"]["mc"]
    assert mca is not None and mca["method"] == "montecarlo"
    assert mca["iterations"] == 4000 and mca["seed"] == 42
    # Seed sama -> distribusi identik (reproducible).
    assert mca["mean"] == pytest.approx(mcb["mean"])
    assert mca["ci_low"] == pytest.approx(mcb["ci_low"])
    assert mca["ci_high"] == pytest.approx(mcb["ci_high"])
    # CI valid & report.uncertainty mengikuti MC.
    assert mca["ci_low"] < mca["mean"] < mca["ci_high"]
    assert a["report"]["uncertainty"]["ci_high"] == pytest.approx(mca["ci_high"])


@pytest.mark.asyncio
async def test_montecarlo_seed_changes_result(client):
    headers = await _auth(client)
    a = await _calc(client, headers, uncertainty_method="montecarlo", mc_seed=1, mc_iterations=4000)
    b = await _calc(client, headers, uncertainty_method="montecarlo", mc_seed=2, mc_iterations=4000)
    assert a["report"]["mc"]["mean"] != pytest.approx(b["report"]["mc"]["mean"])


@pytest.mark.asyncio
async def test_sensitivity_always_present(client):
    headers = await _auth(client)
    rep = (await _calc(client, headers))["report"]
    sens = rep["sensitivity"]
    assert sens and len(sens) == 2  # elec_grid + food_beef
    total_share = sum(s["variance_share"] for s in sens)
    assert total_share == pytest.approx(1.0)
    # Terurut menurun menurut share-varians.
    assert sens[0]["variance_share"] >= sens[1]["variance_share"]


@pytest.mark.asyncio
async def test_analytical_has_no_mc(client):
    headers = await _auth(client)
    rep = (await _calc(client))["report"] if False else (await _calc(client, headers))["report"]
    assert rep["mc"] is None  # default analitis


@pytest.mark.asyncio
async def test_scenario_what_if(client):
    headers = await _auth(client)
    # Buat project + activities lewat domain calculate.
    calc = await _calc(client, headers)
    project_id = calc["project_id"]
    baseline = calc["report"]["total_co2e_kg"]

    # Skenario: grid listrik turun 30% (factor_scale elec_grid = 0.7).
    sc = await client.post(
        f"/projects/{project_id}/scenarios", headers=headers,
        json={"name": "Grid -30%", "overrides": {"factor_scale": {"elec_grid": 0.7}}},
    )
    assert sc.status_code == 201
    sid = sc.json()["id"]

    run = await client.post(f"/projects/{project_id}/scenarios/{sid}/run", headers=headers)
    assert run.status_code == 200
    res = run.json()
    assert res["baseline_total_kg"] == pytest.approx(baseline)
    assert res["scenario_total_kg"] < res["baseline_total_kg"]
    # Hanya elec_grid yang diskalakan: penurunan = 0.3 × emisi listrik baseline.
    elec = next(c for c in res["by_category"] if c["category"] == "elec_grid")
    assert elec["scale"] == pytest.approx(0.7)
    assert elec["delta_kg"] == pytest.approx(-0.3 * elec["baseline_kg"])


@pytest.mark.asyncio
async def test_scenario_unknown_404(client):
    headers = await _auth(client)
    project_id = (await _calc(client, headers))["project_id"]
    r = await client.post(
        f"/projects/{project_id}/scenarios/00000000-0000-0000-0000-000000000000/run",
        headers=headers,
    )
    assert r.status_code == 404
