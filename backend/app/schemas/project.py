"""Pydantic v2 schemas untuk Project, Activity, Run, Result, Scenario."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DataOrigin, Domain, UncertaintyMethod


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Project ---
class ProjectIn(BaseModel):
    name: str
    domain: Domain
    region: str = "GLOBAL"
    gwp_set_id: uuid.UUID
    reporting_period_start: date | None = None
    reporting_period_end: date | None = None
    base_year: int | None = None
    functional_unit: str | None = None
    description: str | None = None


class ProjectOut(ORMModel):
    id: uuid.UUID
    name: str
    domain: str
    region: str
    gwp_set_id: uuid.UUID
    reporting_period_start: date | None
    reporting_period_end: date | None
    base_year: int | None
    functional_unit: str | None
    description: str | None
    created_at: datetime


# --- ActivityRecord ---
class ActivityIn(BaseModel):
    category_id: uuid.UUID
    amount: float
    unit: str
    period: str | None = None
    domain_fields: dict = Field(default_factory=dict)
    data_origin: DataOrigin = DataOrigin.manual
    activity_uncertainty: dict | None = None


class ActivityOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category_id: uuid.UUID
    amount: float
    unit: str
    period: str | None
    domain_fields: dict
    data_origin: str
    activity_uncertainty: dict | None


# --- CalculationRun / Result ---
class RunIn(BaseModel):
    gwp_set_id: uuid.UUID | None = None  # default: gwp_set proyek
    methodology_config: dict = Field(default_factory=dict)
    uncertainty_method: UncertaintyMethod = UncertaintyMethod.analytical


class ResultOut(ORMModel):
    id: uuid.UUID
    run_id: uuid.UUID
    activity_record_id: uuid.UUID
    strategy_used: str
    factor_snapshot: dict
    co2e_kg: float
    co2e_uncertainty: dict | None
    assumptions: dict


class RunOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    created_at: datetime
    gwp_set_id: uuid.UUID
    methodology_config: dict
    uncertainty_method: str
    status: str


class RunDetailOut(RunOut):
    results: list[ResultOut] = Field(default_factory=list)
    total_co2e_kg: float = 0.0


# --- Scenario ---
class ScenarioIn(BaseModel):
    name: str
    overrides: dict = Field(default_factory=dict)


class ScenarioOut(ORMModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    overrides: dict
