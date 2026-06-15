"""Test inti Phase 0: reproducibility, immutability snapshot, GWP, unit conversion."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.engine import recompute_from_snapshot, run_calculation
from app.factors import registry
from app.models.project import ActivityRecord, CalculationRun, Project
from app.models.registry import Category, EmissionFactor, Gas, GWPSet
from app.schemas.registry import EmissionFactorIn


async def _ids(session):
    ar6 = (await session.execute(select(GWPSet).where(GWPSet.name == "AR6"))).scalar_one()
    cats = {c.code: c for c in (await session.execute(select(Category))).scalars().all()}
    gases = {g.symbol: g for g in (await session.execute(select(Gas))).scalars().all()}
    return ar6, cats, gases


async def _make_run(session, project: Project) -> CalculationRun:
    run = CalculationRun(
        project_id=project.id,
        created_at=datetime.now(timezone.utc),
        gwp_set_id=project.gwp_set_id,
        methodology_config={},
        uncertainty_method="analytical",
    )
    session.add(run)
    await session.flush()
    results = await run_calculation(session, run)
    await session.commit()
    return run, results


@pytest.mark.asyncio
async def test_multiply_and_reproducibility(session):
    ar6, cats, _ = await _ids(session)
    proj = Project(
        name="Rumah A", domain="personal", region="ID-Jamali", gwp_set_id=ar6.id,
        reporting_period_end=None,
    )
    session.add(proj)
    await session.flush()
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cats["elec_grid"].id,
        amount=100, unit="kWh", data_origin="manual",
    ))
    await session.commit()

    run, results = await _make_run(session, proj)
    assert len(results) == 1
    r = results[0]
    # 100 kWh * 0.87 kgCO2e/kWh (faktor ID-Jamali) = 87 kg
    assert r.co2e_kg == pytest.approx(87.0)
    assert r.factor_snapshot["region"] == "ID-Jamali"

    # Recompute deterministik dari snapshot beku == angka tersimpan.
    recomputed = recompute_from_snapshot(r.factor_snapshot, 100, "kWh")
    assert recomputed == pytest.approx(r.co2e_kg)

    # Run kedua menghasilkan angka identik (reproducible).
    run2, results2 = await _make_run(session, proj)
    assert run2.id != run.id
    assert results2[0].co2e_kg == pytest.approx(r.co2e_kg)


@pytest.mark.asyncio
async def test_snapshot_immutable_after_factor_new_version(session):
    """Versi faktor baru TIDAK mengubah hasil/snapshot yang sudah dihitung."""
    ar6, cats, gases = await _ids(session)
    proj = Project(name="Rumah B", domain="personal", region="GLOBAL", gwp_set_id=ar6.id)
    session.add(proj)
    await session.flush()
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cats["car_petrol"].id,
        amount=1000, unit="km", data_origin="manual",
    ))
    await session.commit()

    run, results = await _make_run(session, proj)
    original = results[0].co2e_kg
    snapshot = results[0].factor_snapshot

    # Faktor aktif car_petrol (GLOBAL) -> versi baru dengan nilai berbeda.
    active = (await session.execute(
        select(EmissionFactor).where(
            EmissionFactor.category_id == cats["car_petrol"].id,
            EmissionFactor.region == "GLOBAL",
            EmissionFactor.is_active.is_(True),
        )
    )).scalar_one()
    new = await registry.new_version(session, active.id, EmissionFactorIn(
        category_id=active.category_id, gas_id=active.gas_id, source_id=active.source_id,
        value=0.20, unit="kgCO2e/km", region="GLOBAL", gwp_basis="CO2e",
    ))
    await session.commit()
    assert new.version == active.version + 1

    # Recompute dari snapshot LAMA tetap pakai nilai lama (immutable).
    assert recompute_from_snapshot(snapshot, 1000, "km") == pytest.approx(original)

    # Run BARU memakai faktor versi baru -> angka berubah.
    run2, results2 = await _make_run(session, proj)
    assert results2[0].co2e_kg == pytest.approx(0.20 * 1000)
    assert results2[0].co2e_kg != pytest.approx(original)


@pytest.mark.asyncio
async def test_gwp_conversion_per_gas(session):
    """Faktor per-gas (gwp_basis=null) dikonversi ke CO2e via GWP set."""
    ar6, cats, _ = await _ids(session)
    proj = Project(name="Pabrik", domain="organizational", region="GLOBAL", gwp_set_id=ar6.id)
    session.add(proj)
    await session.flush()
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cats["natural_gas"].id,
        amount=1000, unit="kWh", data_origin="manual",
    ))
    await session.commit()

    _, results = await _make_run(session, proj)
    by_gas = {r.factor_snapshot["gas"]["symbol"]: r for r in results}
    assert set(by_gas) == {"CO2", "CH4", "N2O"}

    # CH4: 1000 kWh * 0.000256 kgCH4/kWh * 27.9 (AR6) CO2e
    ch4 = by_gas["CH4"]
    assert ch4.factor_snapshot["gwp_set"]["gwp_applied"] == pytest.approx(27.9)
    assert ch4.co2e_kg == pytest.approx(1000 * 0.000256 * 27.9)
    # CO2: GWP 1
    assert by_gas["CO2"].co2e_kg == pytest.approx(1000 * 0.18316)


@pytest.mark.asyncio
async def test_unit_conversion_mwh_to_kwh(session):
    ar6, cats, _ = await _ids(session)
    proj = Project(name="Gedung", domain="organizational", region="ID-Jamali", gwp_set_id=ar6.id)
    session.add(proj)
    await session.flush()
    # 2 MWh harus dikonversi ke 2000 kWh.
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cats["elec_grid"].id,
        amount=2, unit="MWh", data_origin="manual",
    ))
    await session.commit()

    _, results = await _make_run(session, proj)
    assert results[0].co2e_kg == pytest.approx(2000 * 0.87)


@pytest.mark.asyncio
async def test_uncertainty_band_present(session):
    """Hasil selalu menyimpan rentang ketidakpastian, bukan angka tunggal."""
    ar6, cats, _ = await _ids(session)
    proj = Project(name="Diet", domain="personal", region="GLOBAL", gwp_set_id=ar6.id)
    session.add(proj)
    await session.flush()
    session.add(ActivityRecord(
        project_id=proj.id, category_id=cats["food_beef"].id,
        amount=10, unit="kg", data_origin="manual",
    ))
    await session.commit()

    _, results = await _make_run(session, proj)
    unc = results[0].co2e_uncertainty
    assert unc is not None
    # food_beef pakai dist lognormal (gsd) -> ada sd & CI.
    assert unc["sd"] is not None
    assert unc["ci_low"] < unc["mean"] < unc["ci_high"]
