"""GWP service: konversi massa gas -> CO2e via set GWP terpilih (AR4/AR5/AR6).

Service ini sengaja bebas-ORM: dibangun dari pemetaan {symbol: gwp} agar mudah
diuji dan di-snapshot. CO2 selalu 1 (basis CO2e).
"""

from __future__ import annotations

from dataclasses import dataclass


class GWPError(KeyError):
    """Gas tidak punya nilai GWP pada set terpilih."""


@dataclass(frozen=True)
class GWPService:
    name: str            # mis. "AR6"
    horizon_years: int   # mis. 100
    values: dict[str, float]  # symbol gas -> GWP

    def gwp(self, gas_symbol: str) -> float:
        if gas_symbol == "CO2":
            return 1.0
        try:
            return self.values[gas_symbol]
        except KeyError as exc:  # pragma: no cover - jalur error eksplisit
            raise GWPError(
                f"GWP untuk gas '{gas_symbol}' tidak ada di set '{self.name}'"
            ) from exc

    def to_co2e(self, mass_kg: float, gas_symbol: str) -> float:
        return mass_kg * self.gwp(gas_symbol)

    def snapshot(self) -> dict:
        """Untuk dibekukan di factor_snapshot / methodology appendix."""
        return {"name": self.name, "horizon_years": self.horizon_years}
