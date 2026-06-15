"""Konversi unit berbasis dimensi.

Hanya mengkonversi di dalam dimensi fisik yang sama (energi, massa, volume, jarak).
Unit aktivitas dikonversi ke unit penyebut (denominator) faktor sebelum perkalian.
Unit kompleks/khusus (head, year, ha, pkm, tkm) bersifat identitas (tak dikonversi).
"""

from __future__ import annotations

# unit -> (dimensi, faktor ke unit-basis dimensi tsb)
_UNITS: dict[str, tuple[str, float]] = {
    # Energi — basis kWh
    "kWh": ("energy", 1.0),
    "Wh": ("energy", 0.001),
    "MWh": ("energy", 1000.0),
    "GWh": ("energy", 1_000_000.0),
    "MJ": ("energy", 1.0 / 3.6),
    "GJ": ("energy", 1000.0 / 3.6),
    "kJ": ("energy", 1.0 / 3600.0),
    "kcal": ("energy", 0.00116222),
    # Massa — basis kg
    "kg": ("mass", 1.0),
    "g": ("mass", 0.001),
    "t": ("mass", 1000.0),      # tonne metrik
    "tonne": ("mass", 1000.0),
    "lb": ("mass", 0.45359237),
    # Volume — basis L
    "L": ("volume", 1.0),
    "litre": ("volume", 1.0),
    "mL": ("volume", 0.001),
    "m3": ("volume", 1000.0),
    "gal_us": ("volume", 3.78541),
    # Jarak — basis km
    "km": ("distance", 1.0),
    "m": ("distance", 0.001),
    "mi": ("distance", 1.60934),
}

# Unit yang dibiarkan apa adanya (tidak punya konversi lintas-unit).
_IDENTITY = {
    "head", "year", "ha", "capita", "pkm", "tkm", "each", "unit", "night", "room-night",
}


class UnitError(ValueError):
    """Unit tidak dikenal atau dimensi tidak kompatibel."""


def denominator_of(factor_unit: str) -> str:
    """Ambil unit penyebut dari unit faktor, mis. 'kgCO2e/kWh' -> 'kWh'.

    Untuk penyebut majemuk ('kgCH4/head/year') kembalikan 'head/year' apa adanya.
    """
    if "/" not in factor_unit:
        return factor_unit
    return factor_unit.split("/", 1)[1]


def convert(amount: float, from_unit: str, to_unit: str) -> float:
    """Konversi `amount` dari `from_unit` ke `to_unit` dalam dimensi yang sama."""
    if from_unit == to_unit:
        return amount
    # Penyebut majemuk atau unit identitas: hanya boleh jika identik.
    if from_unit in _IDENTITY or to_unit in _IDENTITY or "/" in to_unit:
        raise UnitError(
            f"Unit aktivitas '{from_unit}' tidak dapat dikonversi ke '{to_unit}'. "
            "Pastikan unit aktivitas sesuai unit penyebut faktor."
        )
    if from_unit not in _UNITS:
        raise UnitError(f"Unit tidak dikenal: '{from_unit}'")
    if to_unit not in _UNITS:
        raise UnitError(f"Unit tidak dikenal: '{to_unit}'")

    dim_from, k_from = _UNITS[from_unit]
    dim_to, k_to = _UNITS[to_unit]
    if dim_from != dim_to:
        raise UnitError(
            f"Dimensi tidak kompatibel: '{from_unit}' ({dim_from}) vs "
            f"'{to_unit}' ({dim_to})"
        )
    return amount * k_from / k_to


def is_known(unit: str) -> bool:
    return unit in _UNITS or unit in _IDENTITY
