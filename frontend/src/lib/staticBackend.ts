// "Backend" in-browser untuk build statis (GitHub Pages). Mengimplementasikan
// subset endpoint yang dipakai UI, dengan data faktor tertanam & engine TS.
// Angka identik dengan backend Python (lihat staticEngine.ts).

import seed from "../data/seed.json";
import type {
  Category,
  EmissionFactor,
  EmissionFactorInput,
  FactorSource,
  Gas,
  GWPSet,
} from "./types";
import {
  convert,
  denominatorOf,
  gwpOf,
  propagateProduct,
  relativeSdFromDist,
  relativeSdFromPct,
  type GWPService,
} from "./staticEngine";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// ---------------- Build entities from seed ----------------
interface RawFactor {
  category: string; gas: string; source: string; value: number; unit: string;
  region: string; gwp_basis?: string | null; tier?: number | null;
  uncertainty_pct?: number | null; dist_type?: string | null;
  dist_params?: Record<string, number> | null; meta?: Record<string, unknown> | null;
}

const sources: Record<string, FactorSource> = {};
for (const s of seed.sources as any[]) {
  sources[s.key] = {
    id: s.key, name: s.name, publisher: s.publisher ?? null, url: s.url ?? null,
    year: s.year ?? null, credibility_tier: s.credibility_tier ?? 2, notes: s.notes ?? null,
  };
}
const gases: Record<string, Gas> = {};
for (const g of seed.gases as any[]) gases[g.symbol] = { id: g.symbol, symbol: g.symbol, name: g.name };

const categories: Record<string, Category> = {};
for (const c of seed.categories as any[]) {
  categories[c.code] = {
    id: c.code, code: c.code, name: c.name, parent_id: null,
    domain_applicability: c.domain_applicability ?? [], scope: c.scope ?? null,
    default_unit: c.default_unit ?? null,
  };
}
const gwpSets: GWPSet[] = (seed.gwp_sets as any[]).map((g) => ({
  id: g.name, name: g.name, horizon_years: g.horizon_years ?? 100, notes: g.notes ?? null,
}));
const gwpValues: Record<string, Record<string, number>> = {};
for (const g of seed.gwp_sets as any[]) gwpValues[g.name] = g.values;

function buildFactor(f: RawFactor, version = 1, validFrom = "2024-01-01T00:00:00Z"): EmissionFactor {
  return {
    id: `${f.category}|${f.gas}|${f.region}|v${version}`,
    category_id: f.category, gas_id: f.gas, source_id: f.source,
    value: f.value, unit: f.unit, region: f.region,
    gwp_basis: f.gwp_basis ?? null, tier: f.tier ?? null,
    version, valid_from: validFrom, valid_to: null, is_active: true,
    dist_type: f.dist_type ?? null, dist_params: f.dist_params ?? null,
    uncertainty_pct: f.uncertainty_pct ?? null, meta: f.meta ?? null,
    gas: gases[f.gas], source: sources[f.source], category: categories[f.category],
  };
}

// State faktor (mutable, persist ke localStorage agar edit bertahan saat demo).
const LS_KEY = "carbon.static.factors";
let factors: EmissionFactor[] = [];
function seedFactors(): EmissionFactor[] {
  return (seed.factors as RawFactor[]).map((f) => buildFactor(f));
}
function load() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    factors = raw ? (JSON.parse(raw) as EmissionFactor[]) : seedFactors();
  } catch {
    factors = seedFactors();
  }
}
function persist() {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(factors));
  } catch { /* abaikan */ }
}
load();

function embed(f: EmissionFactor): EmissionFactor {
  return { ...f, gas: gases[f.gas_id], source: sources[f.source_id], category: categories[f.category_id] };
}

// ---------------- Personal domain (mirror app/domains/personal.py) ----------------
const FIELD_MAP: Record<string, [string, string, number]> = {
  electricity_kwh_month: ["elec_grid", "kWh", 12.0],
  car_km_year: ["car_petrol", "km", 1.0],
  motorcycle_km_year: ["motorcycle", "km", 1.0],
  flight_km_year: ["flight_domestic", "pkm", 1.0],
  beef_kg_week: ["food_beef", "kg", 52.0],
  chicken_kg_week: ["food_chicken", "kg", 52.0],
  lpg_kg_month: ["lpg", "kg", 12.0],
  waste_kg_week: ["waste_landfill", "kg", 52.0],
};

const PERSONAL_BENCHMARKS = {
  unit: "tCO2e/kapita/tahun",
  values: { indonesia_avg: 2.3, world_avg: 4.7, target_2030: 2.0 },
  source: "Indikatif (Global Carbon Project / IEA, perlu sitasi resmi).",
};

const PERSONAL_SCHEMA = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  title: "Kalkulator Karbon Personal",
  type: "object",
  properties: {
    electricity_kwh_month: { type: "number", minimum: 0, title: "Pemakaian listrik",
      "x-ui": { group: "Energi Rumah", unit: "kWh/bulan", help: "Lihat tagihan PLN bulanan.", placeholder: "mis. 250" } },
    lpg_kg_month: { type: "number", minimum: 0, title: "LPG",
      "x-ui": { group: "Energi Rumah", unit: "kg/bulan", help: "Tabung 3kg ≈ 3 kg; 12kg ≈ 12 kg." } },
    car_km_year: { type: "number", minimum: 0, title: "Mobil bensin",
      "x-ui": { group: "Transport", unit: "km/tahun", placeholder: "mis. 12000" } },
    motorcycle_km_year: { type: "number", minimum: 0, title: "Sepeda motor",
      "x-ui": { group: "Transport", unit: "km/tahun" } },
    flight_km_year: { type: "number", minimum: 0, title: "Penerbangan",
      "x-ui": { group: "Transport", unit: "km/tahun", help: "Total jarak tempuh pesawat per tahun." } },
    beef_kg_week: { type: "number", minimum: 0, title: "Daging sapi",
      "x-ui": { group: "Makanan", unit: "kg/minggu" } },
    chicken_kg_week: { type: "number", minimum: 0, title: "Daging ayam",
      "x-ui": { group: "Makanan", unit: "kg/minggu" } },
    waste_kg_week: { type: "number", minimum: 0, title: "Sampah ke TPA",
      "x-ui": { group: "Limbah", unit: "kg/minggu" } },
  },
  "x-groups": ["Energi Rumah", "Transport", "Makanan", "Limbah"],
};

function resolveFactors(categoryCode: string, region: string): EmissionFactor[] {
  const matches = factors.filter(
    (f) => f.category_id === categoryCode && f.is_active && (f.region === region || f.region === "GLOBAL")
  );
  const byGas: Record<string, EmissionFactor> = {};
  for (const f of matches) {
    const cur = byGas[f.gas_id];
    if (!cur || (cur.region === "GLOBAL" && f.region === region)) byGas[f.gas_id] = f;
  }
  return Object.values(byGas);
}

function gwpService(name: string): GWPService {
  const values = gwpValues[name];
  if (!values) throw new ApiError(400, `GWP set '${name}' tidak ada`);
  const set = gwpSets.find((g) => g.name === name)!;
  return { name, horizon_years: set.horizon_years, values };
}

// Snapshot beku (mirror app/core/provenance.build_factor_snapshot) — cukup untuk
// recompute deterministik & sitasi akademik (methodology appendix).
function makeSnapshot(f: EmissionFactor, svc: GWPService, gwpApplied: number) {
  const cat = categories[f.category_id];
  const src = sources[f.source_id];
  return {
    factor_id: f.id, version: f.version, value: f.value, unit: f.unit,
    region: f.region, gwp_basis: f.gwp_basis, tier: f.tier,
    gas: { symbol: f.gas_id, name: gases[f.gas_id]?.name },
    uncertainty: { dist_type: f.dist_type, dist_params: f.dist_params, uncertainty_pct: f.uncertainty_pct },
    source: {
      name: src.name, publisher: src.publisher, url: src.url,
      year: src.year, credibility_tier: src.credibility_tier,
    },
    gwp_set: { name: svc.name, horizon_years: svc.horizon_years, gwp_applied: gwpApplied },
    category: { code: cat.code, name: cat.name, scope: cat.scope },
  };
}

// Methodology appendix (mirror app/domains/base.build_methodology).
function buildMethodology(results: any[]) {
  const seen: Record<string, any> = {};
  for (const r of results) {
    const s = r.factor_snapshot;
    const cat = s.category ?? {};
    const gas = s.gas ?? {};
    const key = s.factor_id || `${cat.code}|${gas.symbol}|${s.region}|${s.version}`;
    if (seen[key]) continue;
    seen[key] = {
      category: cat.code, category_name: cat.name, scope: cat.scope,
      gas: gas.symbol, value: s.value, unit: s.unit, version: s.version,
      region: s.region, gwp_applied: s.gwp_set?.gwp_applied,
      source: s.source ?? {}, uncertainty: s.uncertainty ?? null, tier: s.tier ?? null,
    };
  }
  return Object.values(seen).sort(
    (a: any, b: any) =>
      (a.scope ?? 99) - (b.scope ?? 99) ||
      String(a.category).localeCompare(b.category) ||
      String(a.gas).localeCompare(b.gas)
  );
}

function computePersonal(region: string, gwpName: string, inputs: Record<string, number>) {
  const svc = gwpService(gwpName);
  const results: any[] = [];
  for (const [field, [code, unit, annual]] of Object.entries(FIELD_MAP)) {
    const raw = inputs[field];
    if (raw == null || raw === 0) continue;
    const amount = Number(raw) * annual;
    const fs = resolveFactors(code, region);
    for (const f of fs) {
      const denom = denominatorOf(f.unit);
      const amountConv = convert(amount, unit, denom);
      const gasMass = amountConv * f.value;
      const gwpApplied = f.gwp_basis === "CO2e" ? 1.0 : gwpOf(svc, f.gas_id);
      const co2e = gasMass * gwpApplied;
      const relPct = relativeSdFromPct(f.uncertainty_pct);
      const rel = relPct ?? relativeSdFromDist(f.dist_type, f.dist_params as any);
      const unc = propagateProduct(co2e, [rel]);
      results.push({
        co2e_kg: co2e,
        co2e_uncertainty: unc,
        factor_snapshot: makeSnapshot(f, svc, gwpApplied),
      });
    }
  }
  return aggregatePersonal(results);
}

function aggregatePersonal(results: any[]) {
  const total = results.reduce((a, r) => a + r.co2e_kg, 0);
  const groups: Record<string, any> = {};
  for (const r of results) {
    const cat = r.factor_snapshot.category;
    const g = (groups[cat.code] ??= { code: cat.code, name: cat.name, co2e_kg: 0 });
    g.co2e_kg += r.co2e_kg;
  }
  const breakdown = Object.values(groups).sort((a: any, b: any) => b.co2e_kg - a.co2e_kg);
  for (const g of breakdown as any[]) g.share = total ? g.co2e_kg / total : 0;

  let varSum = 0;
  let hasUnc = false;
  for (const r of results) {
    const sd = r.co2e_uncertainty?.sd;
    if (sd != null) { varSum += sd * sd; hasUnc = true; }
  }
  let uncertainty = null;
  if (hasUnc) {
    const sd = Math.sqrt(varSum);
    uncertainty = { mean: total, sd, ci_low: Math.max(0, total - 1.959963985 * sd), ci_high: total + 1.959963985 * sd };
  }
  const tonnes = total / 1000;
  const comparison: Record<string, any> = {};
  for (const [k, v] of Object.entries(PERSONAL_BENCHMARKS.values))
    comparison[k] = { value: v, ratio: v ? tonnes / v : null };
  const notes: string[] = [];
  if (results.some((r) => r.factor_snapshot.region.startsWith("ID")))
    notes.push("Sebagian faktor (mis. grid Indonesia) masih placeholder — lihat methodology.");

  return {
    domain_id: "personal", total_co2e_kg: total, total_co2e_tonnes: tonnes,
    uncertainty, breakdown, benchmarks: { ...PERSONAL_BENCHMARKS, comparison }, notes,
    methodology: buildMethodology(results),
  };
}

// ---------------- Organizational domain (mirror app/domains/organizational.py) ----------------
const SCOPE_LABELS: Record<number, string> = {
  1: "Scope 1 — Emisi langsung",
  2: "Scope 2 — Energi tidak langsung (listrik dibeli)",
  3: "Scope 3 — Rantai nilai lainnya",
};

const ORG_FACILITY_MAP: Record<string, [string, string]> = {
  natural_gas_kwh: ["natural_gas", "kWh"],
  diesel_stationary_l: ["diesel_stationary", "L"],
  lpg_kg: ["lpg", "kg"],
  electricity_kwh: ["elec_grid", "kWh"],
};
const ORG_LEVEL_MAP: Record<string, [string, string]> = {
  business_travel_air_pkm: ["business_travel_air", "pkm"],
  waste_landfill_kg: ["waste_landfill", "kg"],
};
const ORG_WIDE = "Organisasi (lintas-fasilitas)";

function orgFacilityField(title: string, group: string, unit: string, category: string, extra: object = {}) {
  return { type: "number", minimum: 0, title, "x-ui": { group, unit, category, ...extra } };
}

const ORG_SCHEMA = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  title: "GHG Accounting Organisasi",
  type: "object",
  "x-domain": "organizational",
  properties: {
    facilities: {
      type: "array",
      title: "Fasilitas",
      "x-ui": { widget: "facilities" },
      items: {
        type: "object",
        properties: {
          name: { type: "string", title: "Nama fasilitas", "x-ui": { widget: "text", placeholder: "mis. Pabrik Cikarang" } },
          region: { type: "string", title: "Wilayah grid listrik", "x-ui": { widget: "region" } },
          natural_gas_kwh: orgFacilityField("Gas alam (stasioner)", "Scope 1 — Pembakaran langsung", "kWh/tahun", "natural_gas"),
          diesel_stationary_l: orgFacilityField("Solar (genset/boiler)", "Scope 1 — Pembakaran langsung", "L/tahun", "diesel_stationary"),
          lpg_kg: orgFacilityField("LPG", "Scope 1 — Pembakaran langsung", "kg/tahun", "lpg"),
          electricity_kwh: orgFacilityField("Listrik dibeli (PLN)", "Scope 2 — Energi tidak langsung", "kWh/tahun", "elec_grid"),
        },
      },
    },
    business_travel_air_pkm: orgFacilityField("Perjalanan dinas (udara)", "Scope 3 — Rantai nilai lainnya", "pkm/tahun", "business_travel_air", { scopeLevel: "org" }),
    waste_landfill_kg: orgFacilityField("Limbah ke TPA", "Scope 3 — Rantai nilai lainnya", "kg/tahun", "waste_landfill", { scopeLevel: "org" }),
  },
  "x-groups": [
    "Scope 1 — Pembakaran langsung",
    "Scope 2 — Energi tidak langsung",
    "Scope 3 — Rantai nilai lainnya",
  ],
};

interface OrgSpec { code: string; amount: number; unit: string; facility: string; region: string; }

function orgToSpecs(inputs: any): OrgSpec[] {
  const specs: OrgSpec[] = [];
  const facilities = (inputs.facilities as any[]) ?? [];
  facilities.forEach((fac, idx) => {
    if (!fac || typeof fac !== "object") return;
    const name = (fac.name || `Fasilitas ${idx + 1}`).toString().trim() || `Fasilitas ${idx + 1}`;
    const region = fac.region || "GLOBAL";
    for (const [field, [code, unit]] of Object.entries(ORG_FACILITY_MAP)) {
      const raw = fac[field];
      if (raw == null || raw === 0 || raw === "") continue;
      specs.push({ code, amount: Number(raw), unit, facility: name, region });
    }
  });
  for (const [field, [code, unit]] of Object.entries(ORG_LEVEL_MAP)) {
    const raw = inputs[field];
    if (raw == null || raw === 0 || raw === "") continue;
    specs.push({ code, amount: Number(raw), unit, facility: ORG_WIDE, region: "GLOBAL" });
  }
  return specs;
}

function computeOrg(gwpName: string, inputs: any) {
  const svc = gwpService(gwpName);
  const specs = orgToSpecs(inputs);
  const results: any[] = [];
  for (const spec of specs) {
    const fs = resolveFactors(spec.code, spec.region);
    for (const f of fs) {
      const denom = denominatorOf(f.unit);
      const amountConv = convert(spec.amount, spec.unit, denom);
      const gasMass = amountConv * f.value;
      const gwpApplied = f.gwp_basis === "CO2e" ? 1.0 : gwpOf(svc, f.gas_id);
      const co2e = gasMass * gwpApplied;
      const relPct = relativeSdFromPct(f.uncertainty_pct);
      const rel = relPct ?? relativeSdFromDist(f.dist_type, f.dist_params as any);
      const unc = propagateProduct(co2e, [rel]);
      results.push({
        co2e_kg: co2e,
        co2e_uncertainty: unc,
        facility: spec.facility,
        factor_snapshot: makeSnapshot(f, svc, gwpApplied),
      });
    }
  }
  return aggregateOrg(results);
}

function aggregateOrg(results: any[]) {
  const total = results.reduce((a, r) => a + r.co2e_kg, 0);

  // Breakdown per kategori.
  const groups: Record<string, any> = {};
  for (const r of results) {
    const cat = r.factor_snapshot.category;
    const g = (groups[cat.code] ??= { code: cat.code, name: cat.name, co2e_kg: 0 });
    g.co2e_kg += r.co2e_kg;
  }
  const breakdown = Object.values(groups).sort((a: any, b: any) => b.co2e_kg - a.co2e_kg);
  for (const g of breakdown as any[]) g.share = total ? g.co2e_kg / total : 0;

  // Scope rollup.
  const byScope: Record<number, number> = {};
  for (const r of results) {
    const scope = r.factor_snapshot.category.scope;
    if (scope == null) continue;
    byScope[scope] = (byScope[scope] ?? 0) + r.co2e_kg;
  }
  const scope_rollup = Object.keys(byScope)
    .map(Number).sort((a, b) => a - b)
    .map((s) => ({ scope: s, label: SCOPE_LABELS[s] ?? `Scope ${s}`, co2e_kg: byScope[s], share: total ? byScope[s] / total : 0 }));

  // Facility rollup.
  const facAcc: Record<string, any> = {};
  for (const r of results) {
    const f = (facAcc[r.facility] ??= { name: r.facility, co2e_kg: 0, _by: {} as Record<number, number> });
    f.co2e_kg += r.co2e_kg;
    const scope = r.factor_snapshot.category.scope;
    if (scope != null) f._by[scope] = (f._by[scope] ?? 0) + r.co2e_kg;
  }
  const facility_rollup = Object.values(facAcc).sort((a: any, b: any) => b.co2e_kg - a.co2e_kg);
  for (const f of facility_rollup as any[]) {
    f.share = total ? f.co2e_kg / total : 0;
    f.by_scope = Object.keys(f._by).map(Number).sort((a, b) => a - b)
      .map((s) => ({ scope: s, label: SCOPE_LABELS[s] ?? `Scope ${s}`, co2e_kg: f._by[s] }));
    delete f._by;
  }

  // Ketidakpastian total.
  let varSum = 0; let hasUnc = false;
  for (const r of results) {
    const sd = r.co2e_uncertainty?.sd;
    if (sd != null) { varSum += sd * sd; hasUnc = true; }
  }
  let uncertainty = null;
  if (hasUnc) {
    const sd = Math.sqrt(varSum);
    uncertainty = { mean: total, sd, ci_low: Math.max(0, total - 1.959963985 * sd), ci_high: total + 1.959963985 * sd };
  }

  const notes: string[] = [];
  if (results.some((r) => r.factor_snapshot.region.startsWith("ID")))
    notes.push("Sebagian faktor (mis. grid PLN) masih placeholder — lihat methodology.");
  if (3 in byScope)
    notes.push("Scope 3 baru sebagian (perjalanan dinas & limbah); kategori lain menyusul bertahap.");

  return {
    domain_id: "organizational", total_co2e_kg: total, total_co2e_tonnes: total / 1000,
    uncertainty, breakdown, benchmarks: null, notes, scope_rollup, facility_rollup,
    methodology: buildMethodology(results),
  };
}

// ---------------- Factor CRUD (in-memory + localStorage) ----------------
function now() { return new Date().toISOString(); }

function createFactor(input: EmissionFactorInput): EmissionFactor {
  const prev = factors.find(
    (f) => f.category_id === input.category_id && f.gas_id === input.gas_id &&
      f.region === input.region && f.is_active
  );
  let version = 1;
  if (prev) { prev.is_active = false; prev.valid_to = now(); version = prev.version + 1; }
  const f: EmissionFactor = {
    id: `${input.category_id}|${input.gas_id}|${input.region}|v${version}|${Math.random().toString(36).slice(2, 7)}`,
    category_id: input.category_id, gas_id: input.gas_id, source_id: input.source_id,
    value: input.value, unit: input.unit, region: input.region, gwp_basis: input.gwp_basis,
    tier: input.tier, version, valid_from: now(), valid_to: null, is_active: true,
    dist_type: input.dist_type, dist_params: input.dist_params,
    uncertainty_pct: input.uncertainty_pct, meta: input.meta,
  };
  factors.push(f);
  persist();
  return embed(f);
}

// ---------------- Router ----------------
function match(path: string, pattern: RegExp) {
  return path.match(pattern);
}

export async function staticRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const p = path.split("?")[0];
  const query = new URLSearchParams(path.includes("?") ? path.split("?")[1] : "");

  // Auth (di-bypass; mode statis tanpa server).
  if (p === "/auth/register") return undefined as T;
  if (p === "/auth/token") return { access_token: "static-demo" } as T;
  if (p === "/auth/me") return { email: "demo@local" } as T;
  if (p === "/health") return { status: "ok", db: "static" } as T;

  if (method === "GET") {
    if (p === "/sources") return Object.values(sources) as T;
    if (p === "/gases") return Object.values(gases) as T;
    if (p === "/gwp-sets") return gwpSets as T;
    if (p === "/categories") {
      const domain = query.get("domain");
      let rows = Object.values(categories);
      if (domain) rows = rows.filter((c) => c.domain_applicability.includes(domain));
      return rows as T;
    }
    if (p === "/factors") {
      const categoryId = query.get("category_id");
      const region = query.get("region");
      let rows = factors.filter((f) => f.is_active).map(embed);
      if (categoryId) rows = rows.filter((f) => f.category_id === categoryId);
      if (region) rows = rows.filter((f) => f.region === region);
      return rows as T;
    }
    let m = match(p, /^\/factors\/(.+)\/versions$/);
    if (m) {
      const anchor = factors.find((f) => f.id === m![1]);
      if (!anchor) throw new ApiError(404, "Faktor tidak ditemukan");
      return factors
        .filter((f) => f.category_id === anchor.category_id && f.gas_id === anchor.gas_id && f.region === anchor.region)
        .sort((a, b) => a.version - b.version)
        .map(embed) as T;
    }
    if (p === "/domains")
      return [
        { domain_id: "personal", title: PERSONAL_SCHEMA.title },
        { domain_id: "organizational", title: ORG_SCHEMA.title },
      ] as T;
    m = match(p, /^\/domains\/(.+)\/schema$/);
    if (m) {
      if (m[1] === "personal") return { input_schema: PERSONAL_SCHEMA, benchmarks: PERSONAL_BENCHMARKS } as T;
      if (m[1] === "organizational") return { input_schema: ORG_SCHEMA, benchmarks: null } as T;
      throw new ApiError(404, "Domain belum tersedia");
    }
  }

  if (method === "POST") {
    if (p === "/factors") return createFactor(body as EmissionFactorInput) as T;
    let m = match(p, /^\/factors\/(.+)\/versions$/);
    if (m) {
      const cur = factors.find((f) => f.id === m![1]);
      if (!cur) throw new ApiError(404, "Faktor tidak ditemukan");
      const input = body as EmissionFactorInput;
      return createFactor({ ...input, category_id: cur.category_id, gas_id: cur.gas_id, region: cur.region }) as T;
    }
    m = match(p, /^\/domains\/(.+)\/calculate$/);
    if (m) {
      const b = body as { region?: string; gwp_set_name?: string; inputs?: any };
      let report: any;
      if (m[1] === "personal") {
        report = computePersonal(b.region ?? "GLOBAL", b.gwp_set_name ?? "AR6", b.inputs ?? {});
      } else if (m[1] === "organizational") {
        report = computeOrg(b.gwp_set_name ?? "AR6", b.inputs ?? {});
      } else {
        throw new ApiError(404, "Domain belum tersedia");
      }
      if (report.breakdown.length === 0) throw new ApiError(422, "Tidak ada input yang bisa dihitung.");
      return { project_id: "local", run_id: crypto.randomUUID(), report } as T;
    }
  }

  throw new ApiError(404, `Endpoint statis tidak dikenal: ${method} ${p}`);
}
