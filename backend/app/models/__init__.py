"""Agregasi model agar metadata Base lengkap (penting untuk Alembic & create_all)."""

from app.models.base import Base
from app.models.enums import (
    DataOrigin,
    DistType,
    Domain,
    RunStatus,
    UncertaintyMethod,
)
from app.models.project import (
    ActivityRecord,
    CalculationResult,
    CalculationRun,
    Project,
    Scenario,
)
from app.models.registry import (
    Category,
    EmissionFactor,
    FactorSource,
    Gas,
    GWPSet,
    GWPValue,
)
from app.models.user import User

__all__ = [
    "Base",
    "FactorSource",
    "Gas",
    "GWPSet",
    "GWPValue",
    "Category",
    "EmissionFactor",
    "Project",
    "ActivityRecord",
    "CalculationRun",
    "CalculationResult",
    "Scenario",
    "User",
    "Domain",
    "DistType",
    "DataOrigin",
    "RunStatus",
    "UncertaintyMethod",
]
