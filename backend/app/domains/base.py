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
