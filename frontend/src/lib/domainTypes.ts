// Tipe untuk domain calculator (schema dinamis + report).

export interface UiMeta {
  group?: string;
  unit?: string;
  help?: string;
  placeholder?: string;
  widget?: "text" | "region" | "facilities";  // non-numerik / array (Organizational)
  category?: string;                            // kode kategori faktor (data-driven)
  scopeLevel?: "org";                           // field level-organisasi (lintas-fasilitas)
}

export interface SchemaProperty {
  type: string;
  title: string;
  minimum?: number;
  "x-ui"?: UiMeta;
  items?: { properties: Record<string, SchemaProperty> };  // untuk type: "array"
}

export interface InputSchema {
  title: string;
  properties: Record<string, SchemaProperty>;
  "x-groups"?: string[];
  "x-domain"?: string;
}

export interface Benchmarks {
  unit: string;
  values: Record<string, number>;
  source: string;
  comparison?: Record<string, { value: number; ratio: number | null }>;
}

export interface SchemaResponse {
  input_schema: InputSchema;
  benchmarks: Benchmarks;
}

export interface BreakdownItem {
  code: string;
  name: string;
  co2e_kg: number;
  share: number;
}

export interface Uncertainty {
  mean: number;
  sd: number | null;
  ci_low: number | null;
  ci_high: number | null;
}

export interface ScopeRollupItem {
  scope: number;
  label: string;
  co2e_kg: number;
  share: number;
}

export interface FacilityRollupItem {
  name: string;
  co2e_kg: number;
  share: number;
  by_scope: { scope: number; label: string; co2e_kg: number }[];
}

export interface MethodologyItem {
  category: string;
  category_name: string;
  scope: number | null;
  gas: string;
  value: number;
  unit: string;
  version: number;
  region: string;
  gwp_applied: number;
  tier: number | null;
  source: {
    name?: string;
    publisher?: string | null;
    url?: string | null;
    year?: number | null;
    credibility_tier?: number;
  };
  uncertainty: {
    dist_type?: string | null;
    dist_params?: Record<string, number> | null;
    uncertainty_pct?: number | null;
  } | null;
}

export interface DomainReport {
  domain_id: string;
  total_co2e_kg: number;
  total_co2e_tonnes: number;
  uncertainty: Uncertainty | null;
  breakdown: BreakdownItem[];
  benchmarks: Benchmarks | null;
  notes: string[];
  scope_rollup?: ScopeRollupItem[] | null;
  facility_rollup?: FacilityRollupItem[] | null;
  methodology?: MethodologyItem[] | null;
}

export interface CalcResponse {
  project_id: string;
  run_id: string;
  report: DomainReport;
}
