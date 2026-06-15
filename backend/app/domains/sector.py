"""Domain Sector — pertanian & energi (metode IPCC tier).

Pertanian: CH₄ fermentasi enterik & N₂O manure (lewat strategy IPCC Tier, lihat
`app/core/strategies.py`), N₂O pupuk sintetis & CH₄ sawah (Multiply dgn faktor
ber-unit per kg-N / per ha). Energi: listrik grid & pembakaran solar (reuse faktor).

Satu input populasi sapi memunculkan DUA aktivitas (enterik + manure). Parameter
Tier (GE/Ym, Nex/MS) memakai default pada meta faktor (bersitasi IPCC); bisa
dioverride lewat domain_fields untuk Tier 2. Output: total + breakdown per kategori
(+ catatan tier). Jalur IoT ingestion (sensor → ActivityRecord) lihat `api/ingest.py`.
"""

from __future__ import annotations

import math

from app.domains.base import ActivitySpec, DomainReport, build_methodology
from app.models.project import CalculationResult

# field input -> list of (category_code, unit). Satu field bisa -> beberapa kategori.
FIELD_MAP: dict[str, list[tuple[str, str]]] = {
    "cattle_head": [("enteric_cattle", "head"), ("manure_cattle", "head")],
    "fertilizer_n_kg": [("fert_synthetic_n", "kgN")],  # unit cocok penyebut faktor (kgN2O/kgN)
    "rice_area_ha": [("rice_cultivation", "ha")],
    "electricity_kwh": [("elec_grid", "kWh")],
    "diesel_l": [("diesel_stationary", "L")],
}

_AGRI = {"enteric_cattle", "manure_cattle", "fert_synthetic_n", "rice_cultivation"}


class SectorDomain:
    domain_id = "sector"
    benchmarks = None

    input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Sektor — Pertanian & Energi (IPCC)",
        "type": "object",
        "x-domain": "sector",
        "properties": {
            "cattle_head": {
                "type": "number", "minimum": 0, "title": "Populasi sapi",
                "x-ui": {"group": "Peternakan", "unit": "ekor",
                         "help": "Memunculkan emisi enterik (CH₄) + manure (N₂O), metode IPCC Tier 1."},
            },
            "fertilizer_n_kg": {
                "type": "number", "minimum": 0, "title": "Pupuk N sintetis",
                "x-ui": {"group": "Pertanian", "unit": "kg N/tahun",
                         "help": "Massa nitrogen (bukan massa pupuk). N₂O langsung Tier 1."},
            },
            "rice_area_ha": {
                "type": "number", "minimum": 0, "title": "Luas sawah",
                "x-ui": {"group": "Pertanian", "unit": "ha/musim", "help": "CH₄ sawah per ha per musim."},
            },
            "electricity_kwh": {
                "type": "number", "minimum": 0, "title": "Listrik (pompa/operasi)",
                "x-ui": {"group": "Energi", "unit": "kWh/tahun"},
            },
            "diesel_l": {
                "type": "number", "minimum": 0, "title": "Solar (mesin/genset)",
                "x-ui": {"group": "Energi", "unit": "L/tahun"},
            },
        },
        "x-groups": ["Peternakan", "Pertanian", "Energi"],
    }

    def to_activities(self, raw_input: dict) -> list[ActivitySpec]:
        specs: list[ActivitySpec] = []
        for field_name, targets in FIELD_MAP.items():
            raw = raw_input.get(field_name)
            if raw in (None, "", 0):
                continue
            for code, unit in targets:
                specs.append(
                    ActivitySpec(
                        category_code=code,
                        amount=float(raw),
                        unit=unit,
                        period="annual",
                        domain_fields={"input_field": field_name},
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

        agri = sum(g["co2e_kg"] for g in breakdown if g["code"] in _AGRI)
        notes = [
            "Metode IPCC Tier 1 (faktor default, banyak placeholder) — sesuaikan untuk publikasi.",
        ]
        if total:
            notes.append(
                f"Komposisi: pertanian {agri / total * 100:.0f}% · energi {(total - agri) / total * 100:.0f}%."
            )

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
