"""Pydantic v2 schemas untuk Factor Registry."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DistType


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- FactorSource ---
class FactorSourceIn(BaseModel):
    name: str
    publisher: str | None = None
    url: str | None = None
    year: int | None = None
    credibility_tier: int = Field(default=2, ge=1, le=2)
    notes: str | None = None


class FactorSourceOut(ORMModel):
    id: uuid.UUID
    name: str
    publisher: str | None
    url: str | None
    year: int | None
    credibility_tier: int
    notes: str | None


# --- Gas ---
class GasIn(BaseModel):
    symbol: str
    name: str


class GasOut(ORMModel):
    id: uuid.UUID
    symbol: str
    name: str


# --- GWP ---
class GWPValueOut(ORMModel):
    gas: GasOut
    gwp: float


class GWPSetOut(ORMModel):
    id: uuid.UUID
    name: str
    horizon_years: int
    notes: str | None = None


# --- Category ---
class CategoryIn(BaseModel):
    code: str
    name: str
    parent_id: uuid.UUID | None = None
    domain_applicability: list[str] = Field(default_factory=list)
    scope: int | None = Field(default=None, ge=1, le=3)
    default_unit: str | None = None


class CategoryOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: uuid.UUID | None
    domain_applicability: list[str]
    scope: int | None
    default_unit: str | None


# --- EmissionFactor ---
class EmissionFactorIn(BaseModel):
    category_id: uuid.UUID
    gas_id: uuid.UUID
    source_id: uuid.UUID
    value: float
    unit: str
    region: str = "GLOBAL"
    gwp_basis: str | None = None  # "CO2e" jika sudah CO2e
    tier: int | None = Field(default=None, ge=1, le=3)
    dist_type: DistType | None = None
    dist_params: dict | None = None
    uncertainty_pct: float | None = Field(default=None, ge=0)
    meta: dict | None = None
    valid_from: datetime | None = None  # default: now() saat dibuat


class EmissionFactorOut(ORMModel):
    id: uuid.UUID
    category_id: uuid.UUID
    gas_id: uuid.UUID
    source_id: uuid.UUID
    value: float
    unit: str
    region: str
    gwp_basis: str | None
    tier: int | None
    version: int
    valid_from: datetime
    valid_to: datetime | None
    is_active: bool
    dist_type: str | None
    dist_params: dict | None
    uncertainty_pct: float | None
    meta: dict | None = Field(default=None, alias="meta")

    # Relasi opsional (di-embed saat query detail).
    gas: GasOut | None = None
    source: FactorSourceOut | None = None
    category: CategoryOut | None = None
