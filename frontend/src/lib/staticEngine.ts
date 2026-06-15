// Port TypeScript dari engine backend (app/core/*) — angka HARUS identik.
// Dipakai untuk build statis (GitHub Pages) yang berjalan penuh di browser.

// ---------------- Units (mirror app/core/units.py) ----------------
const UNITS: Record<string, [string, number]> = {
  kWh: ["energy", 1.0], Wh: ["energy", 0.001], MWh: ["energy", 1000.0],
  GWh: ["energy", 1_000_000.0], MJ: ["energy", 1.0 / 3.6], GJ: ["energy", 1000.0 / 3.6],
  kJ: ["energy", 1.0 / 3600.0], kcal: ["energy", 0.00116222],
  kg: ["mass", 1.0], g: ["mass", 0.001], t: ["mass", 1000.0], tonne: ["mass", 1000.0],
  lb: ["mass", 0.45359237],
  L: ["volume", 1.0], litre: ["volume", 1.0], mL: ["volume", 0.001],
  m3: ["volume", 1000.0], gal_us: ["volume", 3.78541],
  km: ["distance", 1.0], m: ["distance", 0.001], mi: ["distance", 1.60934],
};
const IDENTITY = new Set([
  "head", "year", "ha", "capita", "pkm", "tkm", "each", "unit", "night", "room-night",
]);

export function denominatorOf(factorUnit: string): string {
  if (!factorUnit.includes("/")) return factorUnit;
  return factorUnit.slice(factorUnit.indexOf("/") + 1);
}

export function convert(amount: number, from: string, to: string): number {
  if (from === to) return amount;
  if (IDENTITY.has(from) || IDENTITY.has(to) || to.includes("/")) {
    throw new Error(`Unit '${from}' tidak dapat dikonversi ke '${to}'`);
  }
  const f = UNITS[from];
  const tt = UNITS[to];
  if (!f) throw new Error(`Unit tidak dikenal: '${from}'`);
  if (!tt) throw new Error(`Unit tidak dikenal: '${to}'`);
  if (f[0] !== tt[0]) throw new Error(`Dimensi tak kompatibel: ${from} vs ${to}`);
  return (amount * f[1]) / tt[1];
}

// ---------------- Uncertainty (mirror app/core/uncertainty.py) ----------------
const Z95 = 1.959963985;

export function relativeSdFromPct(pct: number | null | undefined): number | null {
  if (pct == null) return null;
  return pct / 100.0 / Z95;
}

export function relativeSdFromDist(
  distType: string | null | undefined,
  params: Record<string, number> | null | undefined
): number | null {
  if (!distType || !params) return null;
  try {
    if (distType === "normal") {
      const { mean, sd } = params;
      return mean ? sd / mean : null;
    }
    if (distType === "lognormal") {
      const gsd = params.gsd;
      if (gsd) {
        const s = Math.log(gsd);
        return Math.sqrt(Math.exp(s * s) - 1.0);
      }
      const sigma = params.sigma;
      if (sigma != null) return Math.sqrt(Math.exp(sigma * sigma) - 1.0);
    }
    if (distType === "uniform") {
      const { low, high } = params;
      const mean = (low + high) / 2.0;
      const sd = (high - low) / Math.sqrt(12.0);
      return mean ? sd / mean : null;
    }
    if (distType === "triangular") {
      const { low, mode, high } = params;
      const mean = (low + mode + high) / 3.0;
      const varv =
        (low * low + mode * mode + high * high - low * mode - low * high - mode * high) / 18.0;
      return mean ? Math.sqrt(varv) / mean : null;
    }
  } catch {
    return null;
  }
  return null;
}

export interface UncertainValue {
  mean: number;
  sd: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export function propagateProduct(mean: number, relativeSds: (number | null)[]): UncertainValue {
  const known = relativeSds.filter((r): r is number => r != null);
  if (known.length === 0) return { mean, sd: null, ci_low: null, ci_high: null };
  const rel = Math.sqrt(known.reduce((a, r) => a + r * r, 0));
  const sd = Math.abs(mean) * rel;
  return { mean, sd, ci_low: mean - Z95 * sd, ci_high: mean + Z95 * sd };
}

// ---------------- GWP ----------------
export interface GWPService {
  name: string;
  horizon_years: number;
  values: Record<string, number>;
}
export function gwpOf(svc: GWPService, gasSymbol: string): number {
  if (gasSymbol === "CO2") return 1.0;
  const v = svc.values[gasSymbol];
  if (v == null) throw new Error(`GWP '${gasSymbol}' tidak ada di set '${svc.name}'`);
  return v;
}

export const Z95_CONST = Z95;
