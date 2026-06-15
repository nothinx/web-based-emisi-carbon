"""Domain Module Contract (§7).

Satu core + domain modules. Tiap domain HANYA berbeda di: (a) input schema,
(b) kategori relevan, (c) strategy (lewat engine), (d) agregasi & output.
Core tidak tahu detail domain; domain tidak menyentuh DB (API layer yang persist).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.models.project import CalculationResult


@dataclass
class ActivitySpec:
    """Spesifikasi aktivitas yang dihasilkan domain dari raw input.

    DB-agnostic: API layer me-resolve `category_code` -> Category.id lalu membuat
    ActivityRecord. Ini menjaga domain module bebas dari DB.
    """

    category_code: str
    amount: float
    unit: str
    period: str | None = None
    domain_fields: dict = field(default_factory=dict)


@dataclass
class DomainReport:
    """Output teragregasi per domain. Bentuk agregasi berbeda tiap domain.

    `scope_rollup` & `facility_rollup` opsional — relevan untuk Organizational
    (GHG Protocol Scope 1/2/3, multi-fasilitas); domain lain membiarkannya None.
    """

    domain_id: str
    total_co2e_kg: float
    total_co2e_tonnes: float
    uncertainty: dict | None             # mean/sd/ci_low/ci_high (kg)
    breakdown: list[dict]                # per kategori: {code,name,co2e_kg,share}
    benchmarks: dict | None              # perbandingan per-kapita dll
    notes: list[str] = field(default_factory=list)
    scope_rollup: list[dict] | None = None     # per scope: {scope,label,co2e_kg,share}
    facility_rollup: list[dict] | None = None  # per fasilitas: {name,co2e_kg,share,by_scope}
    # Methodology appendix: faktor unik terpakai + sitasi (dari snapshot beku).
    # Disertakan di report agar laporan self-contained & dapat dipertahankan
    # secara akademik (lihat §10 spec), juga jalan di demo statis tanpa backend.
    methodology: list[dict] | None = None
    # Phase 3 — distribusi total Monte Carlo (bila uncertainty_method=montecarlo).
    mc: dict | None = None
    # Phase 3 — sensitivity: kontribusi tiap kategori ke varians total (analitis).
    sensitivity: list[dict] | None = None


def build_methodology(results: list[CalculationResult]) -> list[dict]:
    """Daftar faktor unik yang dipakai + sitasi lengkap, dari snapshot beku.

    Dedup per (factor_id) bila ada, jika tidak per (kategori,gas,region,versi).
    Inilah bahan methodology appendix di export laporan.
    """
    seen: dict[str, dict] = {}
    for r in results:
        s = r.factor_snapshot
        cat = s.get("category", {})
        gas = s.get("gas", {})
        key = s.get("factor_id") or (
            f"{cat.get('code')}|{gas.get('symbol')}|{s.get('region')}|{s.get('version')}"
        )
        if key in seen:
            continue
        seen[key] = {
            "category": cat.get("code"),
            "category_name": cat.get("name"),
            "scope": cat.get("scope"),
            "gas": gas.get("symbol"),
            "value": s.get("value"),
            "unit": s.get("unit"),
            "version": s.get("version"),
            "region": s.get("region"),
            "gwp_applied": s.get("gwp_set", {}).get("gwp_applied"),
            "source": s.get("source", {}),
            "uncertainty": s.get("uncertainty"),
            "tier": s.get("tier"),
        }
    return sorted(
        seen.values(),
        key=lambda x: (x["scope"] if x["scope"] is not None else 99, x["category"] or "", x["gas"] or ""),
    )


def mc_items(results: list[CalculationResult]) -> list[tuple]:
    """Ekstrak (mean_co2e, dist_type, dist_params, uncertainty_pct) tiap hasil untuk MC."""
    items: list[tuple] = []
    for r in results:
        unc = (r.factor_snapshot or {}).get("uncertainty") or {}
        items.append((r.co2e_kg, unc.get("dist_type"), unc.get("dist_params"), unc.get("uncertainty_pct")))
    return items


def build_sensitivity(results: list[CalculationResult]) -> list[dict]:
    """Sensitivity analitis: kontribusi tiap kategori ke **varians total** (sd²).

    Menunjukkan kategori/faktor mana yang paling menentukan ketidakpastian hasil —
    pelengkap breakdown emisi (share co2e) dengan share-varians.
    """
    var: dict[str, float] = {}
    name: dict[str, str] = {}
    co2e: dict[str, float] = {}
    total_var = 0.0
    total_co2e = 0.0
    for r in results:
        cat = (r.factor_snapshot or {}).get("category", {})
        code = cat.get("code", "lain")
        name[code] = cat.get("name", code)
        sd = (r.co2e_uncertainty or {}).get("sd") or 0.0
        v = sd * sd
        var[code] = var.get(code, 0.0) + v
        co2e[code] = co2e.get(code, 0.0) + r.co2e_kg
        total_var += v
        total_co2e += r.co2e_kg
    rows = [
        {
            "category": code,
            "name": name[code],
            "variance_share": (var[code] / total_var) if total_var else 0.0,
            "co2e_share": (co2e[code] / total_co2e) if total_co2e else 0.0,
            "sd": var[code] ** 0.5,
        }
        for code in var
    ]
    return sorted(rows, key=lambda x: x["variance_share"], reverse=True)


@runtime_checkable
class DomainModule(Protocol):
    domain_id: str
    input_schema: dict                   # JSON Schema -> render form di frontend
    benchmarks: dict | None

    def to_activities(self, raw_input: dict) -> list[ActivitySpec]: ...
    def aggregate(
        self,
        results: list[CalculationResult],
        activities: list | None = None,
    ) -> DomainReport: ...
