"""Domain Organizational — GHG accounting korporat (GHG Protocol).

Mengikuti GHG Protocol Corporate Standard: emisi dikelompokkan ke
**Scope 1** (pembakaran langsung/milik & dikuasai), **Scope 2** (listrik/energi
yang dibeli), **Scope 3** (rantai nilai — mulai dari perjalanan dinas & limbah).

Mendukung **multi-fasilitas** (tiap fasilitas punya wilayah grid sendiri →
faktor Scope 2 regional) dan **base year**. Strategy: Multiply (cukup untuk
mayoritas Scope 1/2 + Scope 3 berbasis aktivitas).

Output: rollup per scope + rollup per fasilitas (+ breakdown per kategori).
Scope tiap hasil ditentukan dari `category.scope` pada snapshot beku (traceable).

Input schema dirender jadi form dinamis di frontend (array fasilitas + field
level-organisasi). Field input dipetakan ke kategori faktor lewat map di bawah —
nilai faktor tetap berupa data di registry, bukan hardcode.
"""

from __future__ import annotations

import math

from app.domains.base import ActivitySpec, DomainReport
from app.models.project import CalculationResult

# Label scope (GHG Protocol).
SCOPE_LABELS = {
    1: "Scope 1 — Emisi langsung",
    2: "Scope 2 — Energi tidak langsung (listrik dibeli)",
    3: "Scope 3 — Rantai nilai lainnya",
}

# Field per-fasilitas -> (category_code, unit aktivitas). Input sudah basis /tahun.
FACILITY_FIELD_MAP: dict[str, tuple[str, str]] = {
    "natural_gas_kwh": ("natural_gas", "kWh"),       # Scope 1
    "diesel_stationary_l": ("diesel_stationary", "L"),  # Scope 1
    "lpg_kg": ("lpg", "kg"),                          # Scope 1
    "electricity_kwh": ("elec_grid", "kWh"),          # Scope 2 (regional)
}

# Field level-organisasi (lintas-fasilitas) -> (category_code, unit).
ORG_FIELD_MAP: dict[str, tuple[str, str]] = {
    "business_travel_air_pkm": ("business_travel_air", "pkm"),  # Scope 3
    "waste_landfill_kg": ("waste_landfill", "kg"),              # Scope 3
}

_ORG_WIDE = "Organisasi (lintas-fasilitas)"


def _facility_field(title: str, group: str, unit: str, category: str, **extra) -> dict:
    ui = {"group": group, "unit": unit, "category": category}
    ui.update(extra)
    return {"type": "number", "minimum": 0, "title": title, "x-ui": ui}


class OrganizationalDomain:
    domain_id = "organizational"

    # Org tak pakai benchmark per-kapita; intensitas (per pendapatan/karyawan)
    # butuh data tambahan & sitasi -> diserahkan ke laporan (Phase 2b).
    benchmarks = None

    input_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "GHG Accounting Organisasi",
        "type": "object",
        "x-domain": "organizational",
        "properties": {
            "facilities": {
                "type": "array",
                "title": "Fasilitas",
                "x-ui": {"widget": "facilities"},
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string", "title": "Nama fasilitas",
                            "x-ui": {"widget": "text", "placeholder": "mis. Pabrik Cikarang"},
                        },
                        "region": {
                            "type": "string", "title": "Wilayah grid listrik",
                            "x-ui": {"widget": "region"},
                        },
                        "natural_gas_kwh": _facility_field(
                            "Gas alam (stasioner)", "Scope 1 — Pembakaran langsung",
                            "kWh/tahun", "natural_gas"),
                        "diesel_stationary_l": _facility_field(
                            "Solar (genset/boiler)", "Scope 1 — Pembakaran langsung",
                            "L/tahun", "diesel_stationary"),
                        "lpg_kg": _facility_field(
                            "LPG", "Scope 1 — Pembakaran langsung", "kg/tahun", "lpg"),
                        "electricity_kwh": _facility_field(
                            "Listrik dibeli (PLN)", "Scope 2 — Energi tidak langsung",
                            "kWh/tahun", "elec_grid"),
                    },
                },
            },
            "business_travel_air_pkm": _facility_field(
                "Perjalanan dinas (udara)", "Scope 3 — Rantai nilai lainnya",
                "pkm/tahun", "business_travel_air", scopeLevel="org"),
            "waste_landfill_kg": _facility_field(
                "Limbah ke TPA", "Scope 3 — Rantai nilai lainnya",
                "kg/tahun", "waste_landfill", scopeLevel="org"),
        },
        "x-groups": [
            "Scope 1 — Pembakaran langsung",
            "Scope 2 — Energi tidak langsung",
            "Scope 3 — Rantai nilai lainnya",
        ],
    }

    def to_activities(self, raw_input: dict) -> list[ActivitySpec]:
        specs: list[ActivitySpec] = []

        facilities = raw_input.get("facilities") or []
        for idx, fac in enumerate(facilities):
            if not isinstance(fac, dict):
                continue
            name = (fac.get("name") or f"Fasilitas {idx + 1}").strip() or f"Fasilitas {idx + 1}"
            region = fac.get("region") or "GLOBAL"
            for field_name, (code, unit) in FACILITY_FIELD_MAP.items():
                raw = fac.get(field_name)
                if raw in (None, "", 0):
                    continue
                specs.append(
                    ActivitySpec(
                        category_code=code,
                        amount=float(raw),
                        unit=unit,
                        period="annual",
                        domain_fields={
                            "facility": name,
                            "region": region,        # engine resolve faktor per-fasilitas
                            "input_field": field_name,
                        },
                    )
                )

        # Field level-organisasi (Scope 3 lintas-fasilitas).
        for field_name, (code, unit) in ORG_FIELD_MAP.items():
            raw = raw_input.get(field_name)
            if raw in (None, "", 0):
                continue
            specs.append(
                ActivitySpec(
                    category_code=code,
                    amount=float(raw),
                    unit=unit,
                    period="annual",
                    domain_fields={"facility": _ORG_WIDE, "input_field": field_name},
                )
            )
        return specs

    def aggregate(
        self, results: list[CalculationResult], activities: list | None = None
    ) -> DomainReport:
        total = sum(r.co2e_kg for r in results)

        # Peta activity_id -> nama fasilitas (dari domain_fields beku di ActivityRecord).
        facility_of: dict = {}
        for a in activities or []:
            facility_of[a.id] = (a.domain_fields or {}).get("facility", _ORG_WIDE)

        # --- Breakdown per kategori (dari snapshot) ---
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

        # --- Rollup per scope (GHG Protocol) ---
        by_scope: dict[int, float] = {}
        for r in results:
            scope = r.factor_snapshot.get("category", {}).get("scope")
            if scope is None:
                continue
            by_scope[scope] = by_scope.get(scope, 0.0) + r.co2e_kg
        scope_rollup = [
            {
                "scope": s,
                "label": SCOPE_LABELS.get(s, f"Scope {s}"),
                "co2e_kg": by_scope[s],
                "share": (by_scope[s] / total) if total else 0.0,
            }
            for s in sorted(by_scope)
        ]

        # --- Rollup per fasilitas (+ rincian per scope) ---
        fac_acc: dict[str, dict] = {}
        for r in results:
            name = facility_of.get(r.activity_record_id, _ORG_WIDE)
            scope = r.factor_snapshot.get("category", {}).get("scope")
            f = fac_acc.setdefault(name, {"name": name, "co2e_kg": 0.0, "by_scope": {}})
            f["co2e_kg"] += r.co2e_kg
            if scope is not None:
                f["by_scope"][scope] = f["by_scope"].get(scope, 0.0) + r.co2e_kg
        facility_rollup = sorted(fac_acc.values(), key=lambda x: x["co2e_kg"], reverse=True)
        for f in facility_rollup:
            f["share"] = (f["co2e_kg"] / total) if total else 0.0
            # by_scope: dict int->kg menjadi list terurut agar JSON-friendly.
            f["by_scope"] = [
                {"scope": s, "label": SCOPE_LABELS.get(s, f"Scope {s}"), "co2e_kg": v}
                for s, v in sorted(f["by_scope"].items())
            ]

        # --- Ketidakpastian total (kombinasi sd kuadrat, asumsi independen) ---
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
                "mean": total,
                "sd": sd_total,
                "ci_low": max(0.0, total - 1.959963985 * sd_total),
                "ci_high": total + 1.959963985 * sd_total,
            }

        notes: list[str] = []
        if any(
            (r.factor_snapshot.get("source", {}).get("name", "").lower().find("placeholder") >= 0)
            or r.factor_snapshot.get("region", "").startswith("ID")
            for r in results
        ):
            notes.append(
                "Sebagian faktor (mis. grid PLN) masih placeholder — lihat methodology."
            )
        if 3 in by_scope:
            notes.append(
                "Scope 3 baru sebagian (perjalanan dinas & limbah); kategori lain menyusul bertahap."
            )

        return DomainReport(
            domain_id=self.domain_id,
            total_co2e_kg=total,
            total_co2e_tonnes=total / 1000.0,
            uncertainty=uncertainty,
            breakdown=breakdown,
            benchmarks=None,
            notes=notes,
            scope_rollup=scope_rollup,
            facility_rollup=facility_rollup,
        )
