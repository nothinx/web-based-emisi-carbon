// Tipe yang mencerminkan schema backend (app/schemas).

export interface FactorSource {
  id: string;
  name: string;
  publisher: string | null;
  url: string | null;
  year: number | null;
  credibility_tier: number;
  notes: string | null;
}

export interface Gas {
  id: string;
  symbol: string;
  name: string;
}

export interface GWPSet {
  id: string;
  name: string;
  horizon_years: number;
  notes: string | null;
}

export interface Category {
  id: string;
  code: string;
  name: string;
  parent_id: string | null;
  domain_applicability: string[];
  scope: number | null;
  default_unit: string | null;
}

export interface EmissionFactor {
  id: string;
  category_id: string;
  gas_id: string;
  source_id: string;
  value: number;
  unit: string;
  region: string;
  gwp_basis: string | null;
  tier: number | null;
  version: number;
  valid_from: string;
  valid_to: string | null;
  is_active: boolean;
  dist_type: string | null;
  dist_params: Record<string, unknown> | null;
  uncertainty_pct: number | null;
  meta: Record<string, unknown> | null;
  gas?: Gas | null;
  source?: FactorSource | null;
  category?: Category | null;
}

export interface EmissionFactorInput {
  category_id: string;
  gas_id: string;
  source_id: string;
  value: number;
  unit: string;
  region: string;
  gwp_basis: string | null;
  tier: number | null;
  dist_type: string | null;
  dist_params: Record<string, unknown> | null;
  uncertainty_pct: number | null;
  meta: Record<string, unknown> | null;
}
