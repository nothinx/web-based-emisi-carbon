"""Kuantifikasi ketidakpastian.

Phase 0/awal: propagasi analitis (Gaussian error propagation). Untuk perkalian,
relative-errors dikombinasikan secara kuadrat:  (sd/mean)^2 = Σ (sd_i/mean_i)^2.

Phase lanjut (Phase 3): Monte Carlo — sampling distribusi faktor & aktivitas.
Struktur di sini sudah menyiapkan dist_type/dist_params agar tidak retrofit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class UncertainValue:
    """Nilai dengan ketidakpastian. Disimpan, bukan angka tunggal palsu-presisi."""

    mean: float
    sd: float | None = None       # standar deviasi absolut
    ci_low: float | None = None   # batas bawah 95%
    ci_high: float | None = None  # batas atas 95%

    def as_dict(self) -> dict:
        return {
            "mean": self.mean,
            "sd": self.sd,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
        }


def relative_sd_from_pct(uncertainty_pct: float | None) -> float | None:
    """`uncertainty_pct` adalah ±% pada ~95% CI (≈ 2 sd untuk normal).

    Kembalikan relative sd (sd/mean). 20% -> 0.10.
    """
    if uncertainty_pct is None:
        return None
    return (uncertainty_pct / 100.0) / 1.959963985


def relative_sd_from_dist(dist_type: str | None, params: dict | None) -> float | None:
    """Estimasi relative sd dari distribusi faktor (untuk propagasi analitis)."""
    if not dist_type or not params:
        return None
    try:
        if dist_type == "normal":
            mean, sd = params["mean"], params["sd"]
            return sd / mean if mean else None
        if dist_type == "lognormal":
            # gsd = geometric standard deviation; relative sd ≈ sqrt(exp(ln(gsd)^2)-1)
            gsd = params.get("gsd")
            if gsd:
                s = math.log(gsd)
                return math.sqrt(math.exp(s * s) - 1.0)
            sigma = params.get("sigma")  # sd dari ln(x)
            if sigma is not None:
                return math.sqrt(math.exp(sigma * sigma) - 1.0)
        if dist_type == "uniform":
            lo, hi = params["low"], params["high"]
            mean = (lo + hi) / 2.0
            sd = (hi - lo) / math.sqrt(12.0)
            return sd / mean if mean else None
        if dist_type == "triangular":
            lo, mode, hi = params["low"], params["mode"], params["high"]
            mean = (lo + mode + hi) / 3.0
            var = (
                lo * lo + mode * mode + hi * hi
                - lo * mode - lo * hi - mode * hi
            ) / 18.0
            return math.sqrt(var) / mean if mean else None
    except (KeyError, ZeroDivisionError, ValueError):
        return None
    return None


def monte_carlo_total(
    items: list[tuple[float, str | None, dict | None, float | None]],
    iterations: int = 10000,
    seed: int = 12345,
) -> dict:
    """Monte Carlo total dari banyak komponen (mis. hasil per aktivitas/gas).

    Tiap item: (mean_co2e, dist_type, dist_params, uncertainty_pct). Untuk tiap item
    diambil pengali acak (lognormal bila gsd diberikan — menjaga sifat asimetris yang
    jadi alasan utama pakai MC; selain itu normal multiplikatif dari relative-sd).
    Komponen diasumsikan independen (sama seperti propagasi analitis). Seeded → hasil
    **reproducible** (recompute dgn seed sama = angka identik).

    Mengembalikan ringkasan distribusi total: mean, sd, ci 95% (persentil 2.5/97.5),
    median, iterasi, seed.
    """
    import numpy as np

    rng = np.random.default_rng(seed)
    total = np.zeros(iterations)
    for mean, dist_type, params, pct in items:
        if dist_type == "lognormal" and params and params.get("gsd"):
            sigma = math.log(params["gsd"])
            mult = np.exp(sigma * rng.standard_normal(iterations))  # median = 1
        else:
            rel = relative_sd_from_pct(pct)
            if rel is None:
                rel = relative_sd_from_dist(dist_type, params)
            if not rel:
                mult = np.ones(iterations)
            else:
                mult = np.clip(1.0 + rel * rng.standard_normal(iterations), 0.0, None)
        total += mean * mult

    return {
        "mean": float(total.mean()),
        "sd": float(total.std(ddof=1)),
        "ci_low": float(np.percentile(total, 2.5)),
        "ci_high": float(np.percentile(total, 97.5)),
        "p50": float(np.percentile(total, 50)),
        "iterations": iterations,
        "seed": seed,
        "method": "montecarlo",
    }


def propagate_product(mean: float, relative_sds: list[float | None]) -> UncertainValue:
    """Propagasi analitis untuk hasil perkalian (amount × factor × gwp ...).

    Relative-errors yang diketahui dikombinasikan secara kuadrat; yang None diabaikan.
    95% CI diasumsikan ±1.96·sd (pendekatan normal).
    """
    known = [r for r in relative_sds if r is not None]
    if not known:
        return UncertainValue(mean=mean)
    rel = math.sqrt(sum(r * r for r in known))
    sd = abs(mean) * rel
    return UncertainValue(
        mean=mean,
        sd=sd,
        ci_low=mean - 1.959963985 * sd,
        ci_high=mean + 1.959963985 * sd,
    )
