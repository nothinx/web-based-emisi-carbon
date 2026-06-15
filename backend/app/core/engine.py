"""Calculation Engine.

Alur: resolve faktor (kategori + region + period, dgn fallback GLOBAL) → pilih
strategy `applicable` → hitung → konversi gas ke CO2e via GWP set → propagasi
uncertainty → tulis CalculationResult IMMUTABLE dengan factor_snapshot.

Satu kategori+region bisa punya beberapa faktor gas (mis. pembakaran bahan bakar:
CO2+CH4+N2O) — tiap gas menghasilkan satu CalculationResult tersendiri (traceable).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core import units
from app.core.gwp import GWPService
from app.core.provenance import build_factor_snapshot
from app.core.strategies import CalcContext, EmissionResult, select_strategy
from app.models.enums import RunStatus
from app.models.project import (
    ActivityRecord,
    CalculationResult,
    CalculationRun,
    Project,
)
from app.models.registry import EmissionFactor, Gas, GWPSet, GWPValue


class EngineError(ValueError):
    pass


async def build_gwp_service(session: AsyncSession, gwp_set_id: uuid.UUID) -> GWPService:
    gwp_set = (
        await session.execute(
            select(GWPSet)
            .where(GWPSet.id == gwp_set_id)
            .options(selectinload(GWPSet.values).selectinload(GWPValue.gas))
        )
    ).scalar_one_or_none()
    if gwp_set is None:
        raise EngineError(f"GWP set {gwp_set_id} tidak ditemukan")
    values = {v.gas.symbol: v.gwp for v in gwp_set.values}
    return GWPService(name=gwp_set.name, horizon_years=gwp_set.horizon_years, values=values)


async def resolve_factors(
    session: AsyncSession,
    category_id: uuid.UUID,
    region: str,
    at: datetime | None = None,
) -> list[EmissionFactor]:
    """Faktor aktif untuk kategori, satu per gas, region diutamakan lalu fallback GLOBAL.

    `at` memfilter berdasarkan masa berlaku (valid_from/valid_to) bila diberikan.
    """
    stmt = (
        select(EmissionFactor)
        .where(
            EmissionFactor.category_id == category_id,
            EmissionFactor.is_active.is_(True),
            EmissionFactor.region.in_([region, "GLOBAL"]),
        )
        .options(
            selectinload(EmissionFactor.gas),
            selectinload(EmissionFactor.source),
            selectinload(EmissionFactor.category),
        )
    )
    factors = list((await session.execute(stmt)).scalars().all())

    if at is not None:
        def _valid(f: EmissionFactor) -> bool:
            if f.valid_from and f.valid_from > at:
                return False
            if f.valid_to and f.valid_to < at:
                return False
            return True

        factors = [f for f in factors if _valid(f)]

    # Satu faktor per gas: region spesifik mengalahkan GLOBAL.
    by_gas: dict[uuid.UUID, EmissionFactor] = {}
    for f in factors:
        cur = by_gas.get(f.gas_id)
        if cur is None or (cur.region == "GLOBAL" and f.region == region):
            by_gas[f.gas_id] = f
    return list(by_gas.values())


def _compute_one(
    activity: ActivityRecord,
    factor: EmissionFactor,
    gas: Gas,
    ctx: CalcContext,
) -> EmissionResult:
    strategy = select_strategy(factor.category, ctx.methodology_config)
    return strategy.calculate(
        amount=activity.amount,
        amount_unit=activity.unit,
        factor=factor,
        gas=gas,
        ctx=ctx,
    )


async def run_calculation(
    session: AsyncSession, run: CalculationRun
) -> list[CalculationResult]:
    """Eksekusi run: hasilkan CalculationResult immutable untuk tiap (aktivitas, gas)."""
    project = (
        await session.execute(select(Project).where(Project.id == run.project_id))
    ).scalar_one()

    gwp_service = await build_gwp_service(session, run.gwp_set_id)
    ctx = CalcContext(
        gwp=gwp_service,
        region=project.region,
        methodology_config=run.methodology_config or {},
    )

    activities = list(
        (
            await session.execute(
                select(ActivityRecord).where(ActivityRecord.project_id == project.id)
            )
        )
        .scalars()
        .all()
    )

    at = None
    if project.reporting_period_end:
        at = datetime.combine(
            project.reporting_period_end, datetime.min.time(), tzinfo=timezone.utc
        )

    results: list[CalculationResult] = []
    run.status = RunStatus.running.value
    try:
        for activity in activities:
            factors = await resolve_factors(session, activity.category_id, project.region, at)
            if not factors:
                continue  # tidak ada faktor; aktivitas dilewati (dilaporkan di gap)
            for factor in factors:
                gas = factor.gas
                emission = _compute_one(activity, factor, gas, ctx)
                snapshot = build_factor_snapshot(factor, gas, gwp_service)
                result = CalculationResult(
                    run_id=run.id,
                    activity_record_id=activity.id,
                    strategy_used=emission.strategy_used,
                    factor_snapshot=snapshot,
                    co2e_kg=emission.co2e_kg,
                    co2e_uncertainty=emission.uncertainty.as_dict(),
                    assumptions=emission.assumptions,
                )
                session.add(result)
                results.append(result)
        run.status = RunStatus.completed.value
    except Exception:
        run.status = RunStatus.failed.value
        raise

    await session.flush()
    return results


def recompute_from_snapshot(
    snapshot: dict, amount: float, amount_unit: str
) -> float:
    """Recompute deterministik HANYA dari snapshot beku (uji reproducibility).

    Tidak menyentuh DB / faktor live. Harus menghasilkan angka identik dengan run asli.
    """
    denom = units.denominator_of(snapshot["unit"])
    amount_conv = units.convert(amount, amount_unit, denom)
    gas_mass = amount_conv * snapshot["value"]
    gwp_applied = snapshot["gwp_set"]["gwp_applied"]
    return gas_mass * gwp_applied
