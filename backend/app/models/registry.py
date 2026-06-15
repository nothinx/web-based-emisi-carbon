"""Factor Registry: sumber, gas, GWP set, kategori, dan EmissionFactor.

EmissionFactor adalah jantung sistem: multi-source, multi-region, **versioned**.
Edit faktor = baris versi baru (tutup `valid_to` lama, `is_active=False`), bukan
UPDATE in-place. CalculationResult TIDAK boleh mereferensi faktor live; ia
membekukan `factor_snapshot`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import JSONB_PORTABLE, Base, TimestampMixin, UUIDMixin


class FactorSource(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "factor_source"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    year: Mapped[int | None] = mapped_column(Integer)
    # 1 = primary/official, 2 = secondary.
    credibility_tier: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    notes: Mapped[str | None] = mapped_column(String)

    factors: Mapped[list["EmissionFactor"]] = relationship(back_populates="source")

    __table_args__ = (
        CheckConstraint("credibility_tier in (1, 2)", name="credibility_tier_valid"),
    )


class Gas(UUIDMixin, Base):
    __tablename__ = "gas"

    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class GWPSet(UUIDMixin, Base):
    __tablename__ = "gwp_set"

    name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)  # AR4/AR5/AR6
    horizon_years: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    notes: Mapped[str | None] = mapped_column(String)

    values: Mapped[list["GWPValue"]] = relationship(
        back_populates="gwp_set", cascade="all, delete-orphan"
    )


class GWPValue(UUIDMixin, Base):
    __tablename__ = "gwp_value"

    gwp_set_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gwp_set.id", ondelete="CASCADE"), nullable=False
    )
    gas_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gas.id", ondelete="CASCADE"), nullable=False
    )
    gwp: Mapped[float] = mapped_column(Float, nullable=False)

    gwp_set: Mapped[GWPSet] = relationship(back_populates="values")
    gas: Mapped[Gas] = relationship()

    __table_args__ = (
        UniqueConstraint("gwp_set_id", "gas_id", name="gwp_set_gas"),
    )


class Category(UUIDMixin, TimestampMixin, Base):
    """Kategori aktivitas, hierarkis (self-FK)."""

    __tablename__ = "category"

    code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("category.id", ondelete="SET NULL")
    )
    # Array domain (mis. ["personal","organizational"]) — JSON di SQLite, JSONB di PG.
    domain_applicability: Mapped[list[str]] = mapped_column(
        JSONB_PORTABLE, default=list, nullable=False
    )
    # Relevan untuk Organizational; 1/2/3 atau null.
    scope: Mapped[int | None] = mapped_column(Integer)
    default_unit: Mapped[str | None] = mapped_column(String(40))

    parent: Mapped["Category | None"] = relationship(
        remote_side="Category.id", backref="children"
    )

    __table_args__ = (
        CheckConstraint("scope is null or scope in (1,2,3)", name="scope_valid"),
    )


class EmissionFactor(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "emission_factor"

    category_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("category.id", ondelete="RESTRICT"), nullable=False
    )
    gas_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gas.id", ondelete="RESTRICT"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("factor_source.id", ondelete="RESTRICT"), nullable=False
    )

    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(60), nullable=False)  # per-unit aktivitas
    region: Mapped[str] = mapped_column(String(40), default="GLOBAL", nullable=False)

    # Jika faktor sudah dalam CO2e (mis. grid factor kgCO2e/kWh), gwp_basis = "CO2e".
    # Jika faktor per-gas mentah (mis. kgCH4/...), null -> engine konversi via GWP set.
    gwp_basis: Mapped[str | None] = mapped_column(String(20))
    tier: Mapped[int | None] = mapped_column(Integer)  # IPCC 1/2/3

    # Versioning ketat.
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Uncertainty — dibawa sejak awal agar tidak retrofit (meski Phase 0 belum pakai).
    dist_type: Mapped[str | None] = mapped_column(String(20))
    dist_params: Mapped[dict | None] = mapped_column(JSONB_PORTABLE)
    uncertainty_pct: Mapped[float | None] = mapped_column(Float)  # shorthand ±%

    meta: Mapped[dict | None] = mapped_column("metadata", JSONB_PORTABLE)

    category: Mapped[Category] = relationship()
    gas: Mapped[Gas] = relationship()
    source: Mapped[FactorSource] = relationship(back_populates="factors")

    __table_args__ = (
        CheckConstraint("tier is null or tier in (1,2,3)", name="tier_valid"),
        UniqueConstraint(
            "category_id", "gas_id", "region", "version", name="factor_version"
        ),
        # Query panas engine: faktor aktif per kategori+region.
        Index("ix_factor_active_lookup", "category_id", "region", "is_active"),
    )
