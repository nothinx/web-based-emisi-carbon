// Tipe untuk domain calculator (schema dinamis + report).

export interface UiMeta {
  group: string;
  unit: string;
  help?: string;
  placeholder?: string;
}

export interface SchemaProperty {
  type: string;
  title: string;
  minimum?: number;
  "x-ui"?: UiMeta;
}

export interface InputSchema {
  title: string;
  properties: Record<string, SchemaProperty>;
  "x-groups"?: string[];
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

export interface DomainReport {
  domain_id: string;
  total_co2e_kg: number;
  total_co2e_tonnes: number;
  uncertainty: Uncertainty | null;
  breakdown: BreakdownItem[];
  benchmarks: Benchmarks;
  notes: string[];
}

export interface CalcResponse {
  project_id: string;
  run_id: string;
  report: DomainReport;
}
