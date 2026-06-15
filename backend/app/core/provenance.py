"""Provenance: bekukan faktor + sitasi lengkap ke dalam snapshot.

CalculationResult menyimpan snapshot ini, BUKAN referensi ke EmissionFactor live.
Snapshot harus cukup untuk: (a) recompute deterministik, (b) sitasi akademik penuh.
"""

from __future__ import annotations

from app.core.gwp import GWPService
from app.models.registry import EmissionFactor, Gas


def build_factor_snapshot(
    factor: EmissionFactor,
    gas: Gas,
    gwp_service: GWPService,
) -> dict:
    """Bekukan faktor + sumber + GWP yang diterapkan menjadi dict immutable."""
    # Jika faktor sudah CO2e, tidak ada GWP per-gas yang diterapkan.
    gwp_applied = 1.0 if factor.gwp_basis == "CO2e" else gwp_service.gwp(gas.symbol)
    src = factor.source
    return {
        "factor_id": str(factor.id),
        "version": factor.version,
        "value": factor.value,
        "unit": factor.unit,
        "region": factor.region,
        "gwp_basis": factor.gwp_basis,
        "tier": factor.tier,
        "valid_from": factor.valid_from.isoformat() if factor.valid_from else None,
        "valid_to": factor.valid_to.isoformat() if factor.valid_to else None,
        "gas": {"symbol": gas.symbol, "name": gas.name},
        "uncertainty": {
            "dist_type": factor.dist_type,
            "dist_params": factor.dist_params,
            "uncertainty_pct": factor.uncertainty_pct,
        },
        "source": {
            "id": str(src.id),
            "name": src.name,
            "publisher": src.publisher,
            "url": src.url,
            "year": src.year,
            "credibility_tier": src.credibility_tier,
        },
        "gwp_set": {
            "name": gwp_service.name,
            "horizon_years": gwp_service.horizon_years,
            "gwp_applied": gwp_applied,
        },
        "category": {
            "code": factor.category.code,
            "name": factor.category.name,
            "scope": factor.category.scope,
        },
    }
