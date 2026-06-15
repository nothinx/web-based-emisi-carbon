"""Domain Product/LCA — product carbon footprint (parametrik, v1).

**Penyederhanaan yang dinyatakan sebagai limitation** (lihat methodology): bukan
integrasi database LCA komersial, melainkan **parametrik** — faktor per material/proses
(cradle-to-gate proxy) dikalikan kuantitas bill-of-materials, lalu dinormalisasi ke
**functional unit**. Bukan klaim akurasi LCA penuh.

Emisi per functional unit = Σ(kuantitas_material / units_produced × faktor_material).
`units_produced` (default 1) membagi total → impact per 1 functional unit, dgn
breakdown per material tetap proporsional. Strategy: Multiply (faktor sudah CO₂e).
"""

from __future__ import annotations

import math

from app.domains.base import ActivitySpec, DomainReport, build_methodology
from app.models.project import CalculationResult

# field input -> (category_code material, unit)
FIELD_MAP: dict[str, tuple[str, str]] = {
    "steel_kg": ("mat_steel", "kg"),
    "aluminium_kg": ("mat_aluminium", "kg"),
    "plastic_kg": ("mat_plastic", "kg"),
    "cardboard_kg": ("mat_cardboard", "kg"),
    "electricity_kwh": ("elec_grid", "kWh"),       # energi manufaktur
    "transport_tkm": ("mat_transport", "tkm"),     # distribusi
}


class ProductDomain:
    domain_id = "product"
    benchmarks = None

    input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Product Carbon Footprint (LCA parametrik)",
        "type": "object",
        "x-domain": "product",
        "properties": {
            "units_produced": {
                "type": "number", "minimum": 1, "title": "Jumlah unit dinilai",
                "x-ui": {"group": "Functional unit", "unit": "unit",
                         "help": "Total dibagi nilai ini → emisi per 1 functional unit.",
                         "placeholder": "1"},
            },
            "steel_kg": {"type": "number", "minimum": 0, "title": "Baja",
                "x-ui": {"group": "Material", "unit": "kg total"}},
            "aluminium_kg": {"type": "number", "minimum": 0, "title": "Aluminium",
                "x-ui": {"group": "Material", "unit": "kg total"}},
            "plastic_kg": {"type": "number", "minimum": 0, "title": "Plastik (PET)",
                "x-ui": {"group": "Material", "unit": "kg total"}},
            "cardboard_kg": {"type": "number", "minimum": 0, "title": "Kardus/kemasan",
                "x-ui": {"group": "Material", "unit": "kg total"}},
            "electricity_kwh": {"type": "number", "minimum": 0, "title": "Listrik manufaktur",
                "x-ui": {"group": "Proses & distribusi", "unit": "kWh total"}},
            "transport_tkm": {"type": "number", "minimum": 0, "title": "Transport distribusi",
                "x-ui": {"group": "Proses & distribusi", "unit": "tonne-km total",
                         "help": "Massa × jarak (mis. 0.5 t × 300 km = 150 tkm)."}},
        },
        "x-groups": ["Functional unit", "Material", "Proses & distribusi"],
    }

    def to_activities(self, raw_input: dict) -> list[ActivitySpec]:
        try:
            units = float(raw_input.get("units_produced") or 1) or 1.0
        except (TypeError, ValueError):
            units = 1.0
        specs: list[ActivitySpec] = []
        for field_name, (code, unit) in FIELD_MAP.items():
            raw = raw_input.get(field_name)
            if raw in (None, "", 0):
                continue
            per_unit = float(raw) / units  # normalisasi ke functional unit
            specs.append(
                ActivitySpec(
                    category_code=code,
                    amount=per_unit,
                    unit=unit,
                    period=None,
                    domain_fields={"input_field": field_name, "total_input": raw, "units_produced": units},
                )
            )
        return specs

    def aggregate(
        self, results: list[CalculationResult], activities: list | None = None
    ) -> DomainReport:
        total = sum(r.co2e_kg for r in results)

        groups: dict[str, dict] = {}
        for r in results:
            cat = r.factor_snapshot.get("category", {})
            code = cat.get("code", "lain")
            g = groups.setdefault(code, {"code": code, "name": cat.get("name", code), "co2e_kg": 0.0})
            g["co2e_kg"] += r.co2e_kg
        breakdown = sorted(groups.values(), key=lambda x: x["co2e_kg"], reverse=True)
        for g in breakdown:
            g["share"] = (g["co2e_kg"] / total) if total else 0.0

        var = 0.0
        has_unc = False
        for r in results:
            sd = (r.co2e_uncertainty or {}).get("sd")
            if sd is not None:
                var += sd * sd
                has_unc = True
        uncertainty = None
        if has_unc:
            sd_total = math.sqrt(var)
            uncertainty = {
                "mean": total, "sd": sd_total,
                "ci_low": max(0.0, total - 1.959963985 * sd_total),
                "ci_high": total + 1.959963985 * sd_total,
            }

        notes = [
            "LCA v1 parametrik (cradle-to-gate proxy) — bukan integrasi database LCA penuh; "
            "faktor material placeholder. Hasil = kgCO₂e per functional unit.",
        ]

        return DomainReport(
            domain_id=self.domain_id,
            total_co2e_kg=total,
            total_co2e_tonnes=total / 1000.0,
            uncertainty=uncertainty,
            breakdown=breakdown,
            benchmarks=None,
            notes=notes,
            methodology=build_methodology(results),
        )
