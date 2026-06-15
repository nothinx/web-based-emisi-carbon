"""Project, ActivityRecord, CalculationRun, CalculationResult (IMMUTABLE), Scenario.

Aturan keras:
- `CalculationResult` immutable & append-only. Recompute = `CalculationRun` baru.
- Hasil membekukan `factor_snapshot` (JSONB) — TIDAK mereferensi EmissionFactor live.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB_PORTABLE, Base, TimestampMixin, UUIDMixin
from app.models.enums import DataOrigin, Domain, RunStatus, UncertaintyMethod


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("app_user.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(20), nullable=False)
    region: Mapped[str] = mapped_column(String(40), default="GLOBAL", nullable=False)
    reporting_period_start: Mapped[date | None] = mapped_column(Date)
    reporting_period_end: Mapped[date | None] = mapped_column(Date)
    base_year: Mapped[int | None] = mapped_column()
    gwp_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gwp_set.id", ondelete="RESTRICT"), nullable=False
    )
    functional_unit: Mapped[str | None] = mapped_column(String(120))  # untuk LCA
    description: Mapped[str | None] = mapped_column(String)

    gwp_set: Mapped["object"] = relationship("GWPSet")
    activities: Mapped[list["ActivityRecord"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    runs: Mapped[list["CalculationRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ActivityRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "activity_record"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(60), nullable=False)
    period: Mapped[str | None] = mapped_column(String(40))  # mis. "2024", "2024-Q1"
    # Field spesifik domain (mis. jenis bahan bakar, populasi ternak, dll).
    domain_fields: Mapped[dict] = mapped_column(JSONB_PORTABLE, default=dict)
    data_origin: Mapped[str] = mapped_column(
        String(20), default=DataOrigin.manual.value, nullable=False
    )
    activity_uncertainty: Mapped[dict | None] = mapped_column(JSONB_PORTABLE)

    project: Mapped[Project] = relationship(back_populates="activities")
    category: Mapped["object"] = relationship("Category")


class CalculationRun(UUIDMixin, Base):
    __tablename__ = "calculation_run"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    gwp_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gwp_set.id", ondelete="RESTRICT"), nullable=False
    )
    methodology_config: Mapped[dict] = mapped_column(JSONB_PORTABLE, default=dict)
    uncertainty_method: Mapped[str] = mapped_column(
        String(20), default=UncertaintyMethod.none.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=RunStatus.pending.value, nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="runs")
    results: Mapped[list["CalculationResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CalculationResult(UUIDMixin, Base):
    """IMMUTABLE, append-only. Tidak ada UPDATE/DELETE secara logika.

    `factor_snapshot` membekukan: nilai faktor, unit, version, sitasi sumber lengkap,
    dist_params. Inilah yang membuat recompute deterministik & traceable.
    """

    __tablename__ = "calculation_result"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("calculation_run.id", ondelete="CASCADE"), nullable=False
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("activity_record.id", ondelete="RESTRICT"), nullable=False
    )
    strategy_used: Mapped[str] = mapped_column(String(80), nullable=False)

    factor_snapshot: Mapped[dict] = mapped_column(JSONB_PORTABLE, nullable=False)
    co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    co2e_uncertainty: Mapped[dict | None] = mapped_column(JSONB_PORTABLE)
    assumptions: Mapped[dict] = mapped_column(JSONB_PORTABLE, default=dict)

    run: Mapped[CalculationRun] = relationship(back_populates="results")


class Scenario(UUIDMixin, TimestampMixin, Base):
    """What-if / sensitivity: substitusi faktor/aktivitas via overrides (JSONB)."""

    __tablename__ = "scenario"

    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    overrides: Mapped[dict] = mapped_column(JSONB_PORTABLE, default=dict)


__all__ = [
    "Project",
    "ActivityRecord",
    "CalculationRun",
    "CalculationResult",
    "Scenario",
    "Domain",
]
