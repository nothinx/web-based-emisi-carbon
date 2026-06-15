"""Seed loader: muat sumber, gas, GWP set, kategori, & faktor contoh dari JSON.

Idempoten: dijalankan ulang tidak menduplikasi (cek by key alami).
Faktor di-load via service registry (versioning), bukan hardcode di kode.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.factors.registry import create_factor
from app.models.registry import (
    Category,
    FactorSource,
    Gas,
    GWPSet,
    GWPValue,
)
from app.schemas.registry import EmissionFactorIn

SEED_PATH = Path(__file__).resolve().parents[2] / "seed_data" / "seed.json"


async def _get_or_create(session, model, defaults: dict, **lookup):
    obj = (
        await session.execute(select(model).filter_by(**lookup))
    ).scalar_one_or_none()
    if obj:
        return obj, False
    obj = model(**lookup, **defaults)
    session.add(obj)
    await session.flush()
    return obj, True


async def seed(session: AsyncSession, path: Path | None = None) -> dict:
    data = json.loads((path or SEED_PATH).read_text(encoding="utf-8"))
    report = {"sources": 0, "gases": 0, "gwp_sets": 0, "categories": 0, "factors": 0}

    # --- Sources ---
    sources: dict[str, FactorSource] = {}
    for s in data["sources"]:
        obj, created = await _get_or_create(
            session, FactorSource,
            defaults={
                "publisher": s.get("publisher"),
                "url": s.get("url"),
                "year": s.get("year"),
                "credibility_tier": s.get("credibility_tier", 2),
                "notes": s.get("notes"),
            },
            name=s["name"],
        )
        sources[s["key"]] = obj
        report["sources"] += int(created)

    # --- Gases ---
    gases: dict[str, Gas] = {}
    for g in data["gases"]:
        obj, created = await _get_or_create(
            session, Gas, defaults={"name": g["name"]}, symbol=g["symbol"]
        )
        gases[g["symbol"]] = obj
        report["gases"] += int(created)

    # --- GWP sets + values ---
    for gs in data["gwp_sets"]:
        obj, created = await _get_or_create(
            session, GWPSet,
            defaults={"horizon_years": gs.get("horizon_years", 100), "notes": gs.get("notes")},
            name=gs["name"],
        )
        report["gwp_sets"] += int(created)
        if created:
            for sym, val in gs["values"].items():
                session.add(GWPValue(gwp_set_id=obj.id, gas_id=gases[sym].id, gwp=float(val)))
            await session.flush()

    # --- Categories ---
    categories: dict[str, Category] = {}
    for c in data["categories"]:
        obj, created = await _get_or_create(
            session, Category,
            defaults={
                "name": c["name"],
                "domain_applicability": c.get("domain_applicability", []),
                "scope": c.get("scope"),
                "default_unit": c.get("default_unit"),
            },
            code=c["code"],
        )
        categories[c["code"]] = obj
        report["categories"] += int(created)

    # --- Factors (via service registry; idempoten by (category,gas,region) aktif) ---
    from app.models.registry import EmissionFactor

    for f in data["factors"]:
        cat = categories[f["category"]]
        gas = gases[f["gas"]]
        src = sources[f["source"]]
        # Cek apakah sudah ada faktor aktif untuk identitas ini (idempoten).
        already = (
            await session.execute(
                select(EmissionFactor).where(
                    EmissionFactor.category_id == cat.id,
                    EmissionFactor.gas_id == gas.id,
                    EmissionFactor.region == f.get("region", "GLOBAL"),
                    EmissionFactor.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if already:
            continue

        payload = EmissionFactorIn(
            category_id=cat.id,
            gas_id=gas.id,
            source_id=src.id,
            value=f["value"],
            unit=f["unit"],
            region=f.get("region", "GLOBAL"),
            gwp_basis=f.get("gwp_basis"),
            tier=f.get("tier"),
            dist_type=f.get("dist_type"),
            dist_params=f.get("dist_params"),
            uncertainty_pct=f.get("uncertainty_pct"),
            meta=f.get("meta"),
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        )
        await create_factor(session, payload)
        report["factors"] += 1

    await session.commit()
    return report
