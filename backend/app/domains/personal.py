"""Domain Personal — jejak karbon individu/rumah tangga.

Domain paling sederhana; memvalidasi engine end-to-end. Strategy: Multiply.
Output: total ton CO2e/tahun + breakdown per kategori + benchmark per kapita.

Input schema dirender jadi form dinamis di frontend (JSON Schema + ekstensi x-ui).
Tiap field tahunan dipetakan ke kategori faktor lewat FIELD_MAP.
"""

from __future__ import annotations

import math

from app.domains.base import ActivitySpec, DomainReport
from app.models.project import CalculationResult

# field input -> (category_code, unit aktivitas, faktor anualisasi)
# faktor anualisasi: kalikan input ke basis /tahun (bulanan ×12, mingguan ×52).
FIELD_MAP: dict[str, tuple[str, str, float]] = {
    "electricity_kwh_month": ("elec_grid", "kWh", 12.0),
    "car_km_year": ("car_petrol", "km", 1.0),
    "motorcycle_km_year": ("motorcycle", "km", 1.0),
    "flight_km_year": ("flight_domestic", "pkm", 1.0),
    "beef_kg_week": ("food_beef", "kg", 52.0),
    "chicken_kg_week": ("food_chicken", "kg", 52.0),
    "lpg_kg_month": ("lpg", "kg", 12.0),
    "waste_kg_week": ("waste_landfill", "kg", 52.0),
}


class PersonalDomain:
    domain_id = "personal"

    # Sumber benchmark (indikatif): emisi per kapita tahunan (ton CO2e).
    benchmarks = {
        "unit": "tCO2e/kapita/tahun",
        "values": {
            "indonesia_avg": 2.3,   # ~rata-rata Indonesia (energy-related)
            "world_avg": 4.7,       # ~rata-rata dunia
            "target_2030": 2.0,     # ~jalur 1.5°C per kapita
        },
        "source": "Indikatif (Global Carbon Project / IEA, perlu sitasi resmi).",
    }

    input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Kalkulator Karbon Personal",
        "type": "object",
        "properties": {
            "electricity_kwh_month": {
                "type": "number", "minimum": 0, "title": "Pemakaian listrik",
                "x-ui": {"group": "Energi Rumah", "unit": "kWh/bulan",
                         "help": "Lihat tagihan PLN bulanan.", "placeholder": "mis. 250"},
            },
            "lpg_kg_month": {
                "type": "number", "minimum": 0, "title": "LPG",
                "x-ui": {"group": "Energi Rumah", "unit": "kg/bulan",
                         "help": "1 tabung 3kg ≈ 3 kg; 12kg ≈ 12 kg."},
            },
            "car_km_year": {
                "type": "number", "minimum": 0, "title": "Mobil bensin",
                "x-ui": {"group": "Transport", "unit": "km/tahun", "placeholder": "mis. 12000"},
            },
            "motorcycle_km_year": {
                "type": "number", "minimum": 0, "title": "Sepeda motor",
                "x-ui": {"group": "Transport", "unit": "km/tahun"},
            },
            "flight_km_year": {
                "type": "number", "minimum": 0, "title": "Penerbangan",
                "x-ui": {"group": "Transport", "unit": "km/tahun",
                         "help": "Total jarak tempuh pesawat per tahun."},
            },
            "beef_kg_week": {
                "type": "number", "minimum": 0, "title": "Daging sapi",
                "x-ui": {"group": "Makanan", "unit": "kg/minggu"},
            },
            "chicken_kg_week": {
                "type": "number", "minimum": 0, "title": "Daging ayam",
                "x-ui": {"group": "Makanan", "unit": "kg/minggu"},
            },
            "waste_kg_week": {
                "type": "number", "minimum": 0, "title": "Sampah ke TPA",
                "x-ui": {"group": "Limbah", "unit": "kg/minggu"},
            },
        },
        # Urutan grup untuk render.
        "x-groups": ["Energi Rumah", "Transport", "Makanan", "Limbah"],
    }

    def to_activities(self, raw_input: dict) -> list[ActivitySpec]:
        specs: list[ActivitySpec] = []
        for field_name, (code, unit, annual) in FIELD_MAP.items():
            raw = raw_input.get(field_name)
            if raw in (None, "", 0):
                continue
            amount = float(raw) * annual
            specs.append(
                ActivitySpec(
                    category_code=code,
                    amount=amount,
                    unit=unit,
                    period="annual",
                    domain_fields={"input_field": field_name, "input_value": raw},
                )
            )
        return specs

    def aggregate(
        self, results: list[CalculationResult], activities: list | None = None
    ) -> DomainReport:
        # Personal tak butuh metadata aktivitas; agregasi cukup dari hasil.
        total = sum(r.co2e_kg for r in results)

        # Breakdown per kategori (dari snapshot beku).
        groups: dict[str, dict] = {}
        for r in results:
            cat = r.factor_snapshot.get("category", {})
            code = cat.get("code", "lain")
            g = groups.setdefault(
                code, {"code": code, "name": cat.get("name", code), "co2e_kg": 0.0}
            )
            g["co2e_kg"] += r.co2e_kg
        breakdown = sorted(groups.values(), key=lambda x: x["co2e_kg"], reverse=True)
        for g in breakdown:
            g["share"] = (g["co2e_kg"] / total) if total else 0.0

        # Ketidakpastian total: jumlah mean, kombinasi sd kuadrat (asumsi independen).
        var = 0.0
        has_unc = False
        for r in results:
            unc = r.co2e_uncertainty or {}
            sd = unc.get("sd")
            if sd is not None:
                var += sd * sd
                has_unc = True
        uncertainty = None
        if has_unc:
            sd_total = math.sqrt(var)
            uncertainty = {
                "mean": total,
                "sd": sd_total,
                "ci_low": max(0.0, total - 1.959963985 * sd_total),
                "ci_high": total + 1.959963985 * sd_total,
            }

        tonnes = total / 1000.0
        bench = dict(self.benchmarks)
        bench_cmp = {
            k: {"value": v, "ratio": (tonnes / v) if v else None}
            for k, v in self.benchmarks["values"].items()
        }
        bench["comparison"] = bench_cmp

        notes: list[str] = []
        if any(
            (r.factor_snapshot.get("source", {}).get("name", "").lower().find("placeholder") >= 0)
            or r.factor_snapshot.get("region", "").startswith("ID")
            for r in results
        ):
            notes.append(
                "Sebagian faktor (mis. grid Indonesia) masih placeholder — lihat methodology."
            )

        return DomainReport(
            domain_id=self.domain_id,
            total_co2e_kg=total,
            total_co2e_tonnes=tonnes,
            uncertainty=uncertainty,
            breakdown=breakdown,
            benchmarks=bench,
            notes=notes,
        )
