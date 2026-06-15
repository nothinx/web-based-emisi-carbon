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

// ---------------- Monte Carlo (mirror app/core/uncertainty.monte_carlo_total) ----------------
// PRNG mulberry32 (deterministik) + Box-Muller untuk standard normal. Sample path
// berbeda dari numpy di backend, tapi reproducible per-seed & ekuivalen secara
// statistik (estimasi titik/total tetap identik; hanya pita acak yang berbeda path).
function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export interface MCItem {
  mean: number;
  dist_type?: string | null;
  dist_params?: Record<string, number> | null;
  uncertainty_pct?: number | null;
}

export function monteCarloTotal(items: MCItem[], iterations = 10000, seed = 12345) {
  const rand = mulberry32(seed);
  let spare: number | null = null;
  const randn = (): number => {
    if (spare != null) {
      const s = spare;
      spare = null;
      return s;
    }
    let u = 0;
    let v = 0;
    while (u === 0) u = rand();
    while (v === 0) v = rand();
    const mag = Math.sqrt(-2.0 * Math.log(u));
    spare = mag * Math.sin(2 * Math.PI * v);
    return mag * Math.cos(2 * Math.PI * v);
  };

  const totals = new Float64Array(iterations);
  for (const it of items) {
    const dp = it.dist_params ?? null;
    const lognSigma = it.dist_type === "lognormal" && dp && dp.gsd ? Math.log(dp.gsd) : null;
    let rel: number | null = null;
    if (lognSigma == null) {
      rel = relativeSdFromPct(it.uncertainty_pct);
      if (rel == null) rel = relativeSdFromDist(it.dist_type, dp);
    }
    for (let i = 0; i < iterations; i++) {
      let mult: number;
      if (lognSigma != null) mult = Math.exp(lognSigma * randn());
      else if (!rel) mult = 1.0;
      else mult = Math.max(0, 1 + rel * randn());
      totals[i] += it.mean * mult;
    }
  }

  const arr = Array.from(totals);
  const mean = arr.reduce((a, b) => a + b, 0) / iterations;
  const variance = arr.reduce((a, b) => a + (b - mean) ** 2, 0) / (iterations - 1);
  const sorted = arr.slice().sort((a, b) => a - b);
  const pct = (p: number): number => {
    const idx = (p / 100) * (sorted.length - 1);
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    return lo === hi ? sorted[lo] : sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
  };
  return {
    mean, sd: Math.sqrt(variance),
    ci_low: pct(2.5), ci_high: pct(97.5), p50: pct(50),
    iterations, seed, method: "montecarlo",
  };
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
