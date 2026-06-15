"""Calculation strategies (Strategy Pattern).

Engine TIDAK hardcode "perkalian". Tiap strategy mendeklarasikan `applicable()`
dan `calculate()`. Strategy dipilih berdasarkan kategori aktivitas.

Phase 0: MultiplyStrategy. Phase 4 menambah IPCC Tier strategies (enterik, manure)
dan LCAProcessStrategy — cukup daftarkan di STRATEGIES.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.core.gwp import GWPService
from app.core.uncertainty import (
    UncertainValue,
    propagate_product,
    relative_sd_from_dist,
    relative_sd_from_pct,
)
from app.core import units
from app.models.registry import Category, EmissionFactor, Gas


@dataclass
class CalcContext:
    gwp: GWPService
    region: str
    methodology_config: dict = field(default_factory=dict)


@dataclass
class EmissionResult:
    co2e_kg: float
    uncertainty: UncertainValue
    assumptions: dict
    strategy_used: str


class CalculationError(ValueError):
    pass


class CalculationStrategy(ABC):
    id: str

    @abstractmethod
    def applicable(self, category: Category) -> bool: ...

    @abstractmethod
    def calculate(
        self,
        *,
        amount: float,
        amount_unit: str,
        factor: EmissionFactor,
        gas: Gas,
        ctx: CalcContext,
    ) -> EmissionResult: ...


class MultiplyStrategy(CalculationStrategy):
    """Default: co2e = amount × factor.value × gwp.

    Cukup untuk Personal & mayoritas Scope 1/2 Organizational. Mengkonversi unit
    aktivitas ke unit penyebut faktor, lalu mengalikan, lalu konversi ke CO2e via GWP
    (kecuali faktor sudah berbasis CO2e).
    """

    id = "multiply.v1"

    def applicable(self, category: Category) -> bool:  # default fallback
        return True

    def calculate(
        self,
        *,
        amount: float,
        amount_unit: str,
        factor: EmissionFactor,
        gas: Gas,
        ctx: CalcContext,
    ) -> EmissionResult:
        denom = units.denominator_of(factor.unit)
        amount_conv = units.convert(amount, amount_unit, denom)

        # Massa gas (atau CO2e jika faktor sudah CO2e) sebelum GWP.
        gas_mass = amount_conv * factor.value

        if factor.gwp_basis == "CO2e":
            co2e = gas_mass
            gwp_applied = 1.0
        else:
            gwp_applied = ctx.gwp.gwp(gas.symbol)
            co2e = gas_mass * gwp_applied

        # Propagasi ketidakpastian analitis (relative-error perkalian).
        rel_factor = relative_sd_from_pct(factor.uncertainty_pct)
        if rel_factor is None:
            rel_factor = relative_sd_from_dist(factor.dist_type, factor.dist_params)
        uncertainty = propagate_product(co2e, [rel_factor])

        assumptions = {
            "strategy": self.id,
            "amount_input": amount,
            "amount_input_unit": amount_unit,
            "amount_converted": amount_conv,
            "factor_denominator_unit": denom,
            "factor_value": factor.value,
            "gwp_basis": factor.gwp_basis,
            "gwp_applied": gwp_applied,
            "gwp_set": ctx.gwp.name,
        }
        return EmissionResult(
            co2e_kg=co2e,
            uncertainty=uncertainty,
            assumptions=assumptions,
            strategy_used=self.id,
        )


# Daftar strategy berurutan; engine pilih yang pertama `applicable`.
# Strategy spesifik (Tier IPCC, LCA) didaftarkan SEBELUM MultiplyStrategy nanti.
STRATEGIES: list[CalculationStrategy] = [
    MultiplyStrategy(),
]


def select_strategy(
    category: Category, methodology_config: dict | None = None
) -> CalculationStrategy:
    """Pilih strategy. `methodology_config.strategy_override` bisa memaksa satu id."""
    override = (methodology_config or {}).get("strategy_override")
    if override:
        for s in STRATEGIES:
            if s.id == override:
                return s
        raise CalculationError(f"Strategy override tidak dikenal: {override}")
    for s in STRATEGIES:
        if s.applicable(category):
            return s
    raise CalculationError(f"Tidak ada strategy untuk kategori {category.code}")
