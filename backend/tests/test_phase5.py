"""Phase 5 — Product/LCA parametrik: BOM × faktor material, normalisasi functional unit."""

from __future__ import annotations

import pytest

from app.domains.product import ProductDomain


def test_to_activities_normalizes_per_functional_unit():
    dom = ProductDomain()
    specs = dom.to_activities({"units_produced": 10, "steel_kg": 100, "plastic_kg": 0})
    by = {s.category_code: s for s in specs}
    # 100 kg baja / 10 unit = 10 kg/unit; nilai 0 dilewati.
    assert by["mat_steel"].amount == pytest.approx(10.0)
    assert "mat_plastic" not in by


async def _auth(client) -> dict:
    await client.post("/auth/register", json={"email": "p5@uji.id", "password": "rahasia123"})
    tok = await client.post("/auth/token", data={"username": "p5@uji.id", "password": "rahasia123"})
    return {"Authorization": f"Bearer {tok.json()['access_token']}"}


@pytest.mark.asyncio
async def test_product_lca_breakdown_per_unit(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/product/calculate", headers=headers,
        json={"gwp_set_name": "AR6", "inputs": {
            "units_produced": 100,
            "steel_kg": 200,        # 2 kg/unit × 2.0 = 4.0
            "aluminium_kg": 50,     # 0.5 kg/unit × 8.0 = 4.0
            "transport_tkm": 1000,  # 10 tkm/unit × 0.107 = 1.07
        }},
    )
    assert r.status_code == 200
    report = r.json()["report"]
    bd = {b["code"]: b["co2e_kg"] for b in report["breakdown"]}
    assert bd["mat_steel"] == pytest.approx((200 / 100) * 2.0)
    assert bd["mat_aluminium"] == pytest.approx((50 / 100) * 8.0)
    assert bd["mat_transport"] == pytest.approx((1000 / 100) * 0.107)
    # Total per functional unit.
    assert report["total_co2e_kg"] == pytest.approx(4.0 + 4.0 + 1.07)
    # Limitation parametrik dinyatakan.
    assert any("parametrik" in n.lower() for n in report["notes"])
    assert report["methodology"]


@pytest.mark.asyncio
async def test_product_default_units_is_one(client):
    headers = await _auth(client)
    r = await client.post(
        "/domains/product/calculate", headers=headers,
        json={"gwp_set_name": "AR6", "inputs": {"plastic_kg": 3}},  # tanpa units_produced
    )
    report = r.json()["report"]
    # default units=1 → 3 kg × 3.0 = 9.0
    assert report["total_co2e_kg"] == pytest.approx(3 * 3.0)


@pytest.mark.asyncio
async def test_all_four_domains_listed(client):
    r = await client.get("/domains")
    ids = {d["domain_id"] for d in r.json()}
    assert {"personal", "organizational", "sector", "product"} == ids
