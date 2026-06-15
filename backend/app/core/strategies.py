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
        domain_fields: dict | None = None,
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
        domain_fields: dict | None = None,
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


class IPCCEntericTier2Strategy(CalculationStrategy):
    """CH₄ fermentasi enterik ternak (IPCC 2006/2019, Vol.4 Ch.10).

    Tier 2 bila `domain_fields` memberi gross energy & methane conversion:
        EF [kg CH₄/ekor/thn] = GE × (Ym/100) × 365 / 55.65
    (55.65 MJ/kg CH₄). Jika tidak, Tier 1: pakai `factor.value` sebagai EF default
    per ekor (bersitasi IPCC). Lalu CH₄ = populasi × EF, dikonversi ke CO₂e via GWP.
    Bukan perkalian tunggal: EF bisa dihitung dari karakteristik populasi.
    """

    id = "ipcc.enteric.v2"
    MJ_PER_KG_CH4 = 55.65

    def applicable(self, category: Category) -> bool:
        return category.code.startswith("enteric_")

    def calculate(self, *, amount, amount_unit, factor, gas, ctx, domain_fields=None):
        df = domain_fields or {}
        meta = factor.meta or {}
        population = amount  # 'head' (count) — tidak dikonversi unit
        ge = df.get("gross_energy_mj_per_day", meta.get("ge_mj_per_day"))
        ym = df.get("methane_conversion_pct", meta.get("ym_pct"))
        if ge is not None and ym is not None:
            ef = ge * (ym / 100.0) * 365.0 / self.MJ_PER_KG_CH4
            tier = 2
        else:
            ef = factor.value  # Tier 1 default EF (kg CH4/head/yr)
            tier = 1
        ch4 = population * ef
        gwp_applied = ctx.gwp.gwp(gas.symbol)
        co2e = ch4 * gwp_applied

        rel = relative_sd_from_pct(factor.uncertainty_pct) or relative_sd_from_dist(
            factor.dist_type, factor.dist_params
        )
        uncertainty = propagate_product(co2e, [rel])
        return EmissionResult(
            co2e_kg=co2e,
            uncertainty=uncertainty,
            assumptions={
                "strategy": self.id, "tier": tier, "population_head": population,
                "ef_kg_ch4_per_head_yr": ef, "ge_mj_per_day": ge, "ym_pct": ym,
                "gwp_applied": gwp_applied, "ch4_kg": ch4,
            },
            strategy_used=self.id,
        )


class IPCCManureN2OStrategy(CalculationStrategy):
    """N₂O langsung dari pengelolaan kotoran ternak (IPCC Tier 1, Vol.4 Ch.10/11).

        N₂O = populasi × Nex × MS × EF3 × (44/28)
    Nex = ekskresi N (kg N/ekor/thn), MS = fraksi pada sistem pengelolaan,
    EF3 = faktor emisi N₂O-N (kg N₂O-N/kg N) = `factor.value`. 44/28 = konversi N→N₂O.
    Multi-parameter (bukan perkalian tunggal); Nex/MS dari domain_fields atau default
    faktor (meta), EF3 dari faktor. Dikonversi ke CO₂e via GWP N₂O.
    """

    id = "ipcc.manure_n2o.v1"
    N_TO_N2O = 44.0 / 28.0

    def applicable(self, category: Category) -> bool:
        return category.code.startswith("manure_")

    def calculate(self, *, amount, amount_unit, factor, gas, ctx, domain_fields=None):
        df = domain_fields or {}
        meta = factor.meta or {}
        population = amount
        nex = df.get("n_excretion_kg_per_head_yr", meta.get("nex_kg_per_head_yr"))
        ms = df.get("manure_system_fraction", meta.get("ms_fraction", 1.0))
        ef3 = factor.value
        if nex is None:
            raise CalculationError(
                "Manure N2O butuh 'n_excretion_kg_per_head_yr' (domain_fields atau meta faktor)."
            )
        n2o = population * nex * ms * ef3 * self.N_TO_N2O
        gwp_applied = ctx.gwp.gwp(gas.symbol)
        co2e = n2o * gwp_applied

        rel = relative_sd_from_pct(factor.uncertainty_pct) or relative_sd_from_dist(
            factor.dist_type, factor.dist_params
        )
        uncertainty = propagate_product(co2e, [rel])
        return EmissionResult(
            co2e_kg=co2e,
            uncertainty=uncertainty,
            assumptions={
                "strategy": self.id, "tier": 1, "population_head": population,
                "nex_kg_per_head_yr": nex, "manure_system_fraction": ms, "ef3": ef3,
                "n_to_n2o": self.N_TO_N2O, "gwp_applied": gwp_applied, "n2o_kg": n2o,
            },
            strategy_used=self.id,
        )


# Daftar strategy berurutan; engine pilih yang pertama `applicable`.
# Strategy spesifik (Tier IPCC) didaftarkan SEBELUM MultiplyStrategy (fallback).
STRATEGIES: list[CalculationStrategy] = [
    IPCCEntericTier2Strategy(),
    IPCCManureN2OStrategy(),
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
