"""Enum domain (disimpan sebagai string agar portable & mudah diperluas)."""

from __future__ import annotations

from enum import StrEnum


class Domain(StrEnum):
    personal = "personal"
    organizational = "organizational"
    product = "product"
    sector = "sector"


class DistType(StrEnum):
    lognormal = "lognormal"
    normal = "normal"
    uniform = "uniform"
    triangular = "triangular"


class DataOrigin(StrEnum):
    manual = "manual"
    import_ = "import"
    sensor = "sensor"


class UncertaintyMethod(StrEnum):
    none = "none"
    analytical = "analytical"
    montecarlo = "montecarlo"


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
