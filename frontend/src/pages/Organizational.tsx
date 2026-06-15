import { useMemo, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import type { CalcResponse, InputSchema, SchemaProperty, SchemaResponse } from "../lib/domainTypes";
import type { GWPSet } from "../lib/types";
import { Button, EmptyState, Spinner } from "../components/ui";
import { BreakdownBars, ScopeRollup, SensitivityBars } from "../components/charts";
import { ReportActions, ReportPrint } from "../components/ReportPanel";
import { fmtNumber } from "../lib/format";
import "./calculator.css";
import "./organizational.css";

const REGIONS = [
  { value: "ID-Jamali", label: "Jawa–Madura–Bali (PLN Jamali)" },
  { value: "ID-Sumatera", label: "Sumatera (PLN)" },
  { value: "GLOBAL", label: "Global (fallback)" },
];

interface Field {
  key: string;
  title: string;
  unit: string;
  help?: string;
  placeholder?: string;
}
interface Group {
  group: string;
  fields: Field[];
}

// Bangun grup field numerik dari record properti schema (urut sesuai x-groups).
function buildGroups(props: Record<string, SchemaProperty>, order: string[]): Group[] {
  const byGroup = new Map<string, Field[]>();
  for (const [key, prop] of Object.entries(props)) {
    if (prop.type !== "number") continue; // lewati name/region/array
    const ui = prop["x-ui"] ?? {};
    const group = ui.group ?? "Lainnya";
    const arr = byGroup.get(group) ?? [];
    arr.push({ key, title: prop.title, unit: ui.unit ?? "", help: ui.help, placeholder: ui.placeholder });
    byGroup.set(group, arr);
  }
  const ordered = [...order, ...[...byGroup.keys()].filter((g) => !order.includes(g))];
  return ordered.filter((g) => byGroup.has(g)).map((g) => ({ group: g, fields: byGroup.get(g)! }));
}

interface FacilityState {
  name: string;
  region: string;
  values: Record<string, string>;
}

function newFacility(n: number): FacilityState {
  return { name: `Fasilitas ${n}`, region: "ID-Jamali", values: {} };
}

export function Organizational() {
  const schema = useAsync(() => api.get<SchemaResponse>("/domains/organizational/schema"), []);
  const gwps = useAsync(() => api.get<GWPSet[]>("/gwp-sets"), []);

  const [orgName, setOrgName] = useState("");
  const [baseYear, setBaseYear] = useState(String(new Date().getFullYear() - 1));
  const [gwpName, setGwpName] = useState("AR6");
  const [method, setMethod] = useState<"analytical" | "montecarlo">("analytical");
  const [facilities, setFacilities] = useState<FacilityState[]>([newFacility(1)]);
  const [orgInputs, setOrgInputs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CalcResponse | null>(null);

  const { facilityGroups, orgGroups } = useMemo(() => {
    const s = schema.data?.input_schema as InputSchema | undefined;
    if (!s) return { facilityGroups: [] as Group[], orgGroups: [] as Group[] };
    const order = s["x-groups"] ?? [];
    const facItems = s.properties.facilities?.items?.properties ?? {};
    return {
      facilityGroups: buildGroups(facItems, order),
      orgGroups: buildGroups(s.properties, order),
    };
  }, [schema.data]);

  function setFacValue(idx: number, key: string, val: string) {
    setFacilities((fs) => fs.map((f, i) => (i === idx ? { ...f, values: { ...f.values, [key]: val } } : f)));
  }
  function setFacMeta(idx: number, patch: Partial<FacilityState>) {
    setFacilities((fs) => fs.map((f, i) => (i === idx ? { ...f, ...patch } : f)));
  }

  const hasInput =
    facilities.some((f) => Object.values(f.values).some((v) => v !== "" && Number(v) > 0)) ||
    Object.values(orgInputs).some((v) => v !== "" && Number(v) > 0);

  async function submit() {
    setBusy(true);
    setError(null);
    const facPayload = facilities.map((f) => {
      const obj: Record<string, string | number> = { name: f.name || "Fasilitas", region: f.region };
      for (const [k, v] of Object.entries(f.values)) {
        if (v !== "" && !Number.isNaN(Number(v))) obj[k] = Number(v);
      }
      return obj;
    });
    const orgNumeric: Record<string, number> = {};
    for (const [k, v] of Object.entries(orgInputs)) {
      if (v !== "" && !Number.isNaN(Number(v))) orgNumeric[k] = Number(v);
    }
    try {
      const res = await api.post<CalcResponse>("/domains/organizational/calculate", {
        name: orgName || undefined,
        gwp_set_name: gwpName,
        base_year: baseYear ? Number(baseYear) : undefined,
        uncertainty_method: method,
        inputs: { facilities: facPayload, ...orgNumeric },
      });
      setResult(res);
      requestAnimationFrame(() =>
        document.getElementById("result")?.scrollIntoView({ behavior: "smooth", block: "start" })
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Gagal menghitung");
    } finally {
      setBusy(false);
    }
  }

  if (schema.loading || gwps.loading)
    return (
      <div className="loading-row">
        <Spinner /> Memuat kalkulator…
      </div>
    );
  if (schema.error) return <EmptyState title="Gagal memuat schema" hint={schema.error} />;

  return (
    <div className="calc">
      <header className="page-head">
        <div>
          <h1>GHG Accounting Organisasi</h1>
          <p className="page-sub">
            Inventarisasi emisi korporat per <strong>GHG Protocol</strong> (Scope 1/2/3),
            multi-fasilitas dengan faktor grid regional. Hasil tersimpan, bersitasi, &{" "}
            <strong>reproducible</strong>.
          </p>
        </div>
      </header>

      <div className="calc-grid">
        <section className="calc-form">
          <div className="calc-context org-context">
            <label className="ctx-field">
              <span>Nama organisasi</span>
              <input className="control" placeholder="mis. PT Contoh" value={orgName}
                onChange={(e) => setOrgName(e.target.value)} />
            </label>
            <label className="ctx-field">
              <span>Base year</span>
              <input className="control" type="number" inputMode="numeric" value={baseYear}
                onChange={(e) => setBaseYear(e.target.value)} />
            </label>
            <label className="ctx-field">
              <span>GWP set</span>
              <select className="control" value={gwpName} onChange={(e) => setGwpName(e.target.value)}>
                {(gwps.data ?? []).map((g) => (
                  <option key={g.id} value={g.name}>
                    {g.name} ({g.horizon_years}thn)
                  </option>
                ))}
              </select>
            </label>
            <label className="ctx-field">
              <span>Ketidakpastian</span>
              <select className="control" value={method}
                onChange={(e) => setMethod(e.target.value as "analytical" | "montecarlo")}>
                <option value="analytical">Analitis (Gaussian)</option>
                <option value="montecarlo">Monte Carlo</option>
              </select>
            </label>
          </div>

          {facilities.map((fac, idx) => (
            <fieldset className="calc-group facility-card" key={idx}>
              <legend>
                <span className="facility-tag">Fasilitas {idx + 1}</span>
                {facilities.length > 1 ? (
                  <button type="button" className="facility-remove"
                    onClick={() => setFacilities((fs) => fs.filter((_, i) => i !== idx))}>
                    Hapus
                  </button>
                ) : null}
              </legend>

              <div className="facility-meta">
                <label className="calc-field">
                  <span className="calc-field-label">Nama fasilitas</span>
                  <div className="calc-input">
                    <input type="text" value={fac.name} placeholder="mis. Pabrik Cikarang"
                      onChange={(e) => setFacMeta(idx, { name: e.target.value })} />
                  </div>
                </label>
                <label className="calc-field">
                  <span className="calc-field-label">Wilayah grid listrik</span>
                  <div className="calc-input">
                    <select className="control" value={fac.region}
                      onChange={(e) => setFacMeta(idx, { region: e.target.value })}>
                      {REGIONS.map((r) => (
                        <option key={r.value} value={r.value}>{r.label}</option>
                      ))}
                    </select>
                  </div>
                </label>
              </div>

              {facilityGroups.map((g) => (
                <div className="facility-scope" key={g.group}>
                  <div className="scope-head">{g.group}</div>
                  <div className="calc-fields">
                    {g.fields.map((f) => (
                      <label className="calc-field" key={f.key}>
                        <span className="calc-field-label">{f.title}</span>
                        <div className="calc-input">
                          <input type="number" min={0} step="any" inputMode="decimal"
                            placeholder={f.placeholder ?? "0"}
                            value={fac.values[f.key] ?? ""}
                            onChange={(e) => setFacValue(idx, f.key, e.target.value)} />
                          <span className="calc-unit">{f.unit}</span>
                        </div>
                        {f.help ? <span className="calc-help">{f.help}</span> : null}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </fieldset>
          ))}

          <button type="button" className="facility-add"
            onClick={() => setFacilities((fs) => [...fs, newFacility(fs.length + 1)])}>
            + Tambah fasilitas
          </button>

          {orgGroups.length ? (
            <fieldset className="calc-group">
              <legend>Tingkat organisasi (lintas-fasilitas)</legend>
              {orgGroups.map((g) => (
                <div className="facility-scope" key={g.group}>
                  <div className="scope-head">{g.group}</div>
                  <div className="calc-fields">
                    {g.fields.map((f) => (
                      <label className="calc-field" key={f.key}>
                        <span className="calc-field-label">{f.title}</span>
                        <div className="calc-input">
                          <input type="number" min={0} step="any" inputMode="decimal"
                            placeholder={f.placeholder ?? "0"}
                            value={orgInputs[f.key] ?? ""}
                            onChange={(e) => setOrgInputs({ ...orgInputs, [f.key]: e.target.value })} />
                          <span className="calc-unit">{f.unit}</span>
                        </div>
                        {f.help ? <span className="calc-help">{f.help}</span> : null}
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </fieldset>
          ) : null}

          {error ? <div className="login-error">{error}</div> : null}
          <Button variant="primary" onClick={submit} loading={busy} disabled={!hasInput}>
            Hitung Emisi
          </Button>
        </section>

        <aside className="calc-result" id="result">
          {result ? (
            <OrgResult data={result} />
          ) : (
            <div className="result-placeholder">
              <div className="rp-mark" aria-hidden>
                CO<sub>2</sub>e
              </div>
              <p>
                Hasil akan muncul di sini: total <strong>tCO₂e</strong>, rollup{" "}
                <strong>Scope 1/2/3</strong>, dan rincian per fasilitas & kategori.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function OrgResult({ data }: { data: CalcResponse }) {
  const r = data.report;
  const unc = r.uncertainty;
  return (
    <div className="result">
      <div className="result-hero">
        <span className="rh-label">Total emisi organisasi</span>
        <div className="rh-value mono">
          {r.total_co2e_tonnes.toFixed(2)}
          <span className="rh-unit">tCO₂e/tahun</span>
        </div>
        {unc && unc.ci_low != null && unc.ci_high != null ? (
          <span className="rh-ci mono">
            95% CI: {(unc.ci_low / 1000).toFixed(2)} – {(unc.ci_high / 1000).toFixed(2)} t
            {r.mc ? ` · Monte Carlo N=${r.mc.iterations}` : " · analitis"}
          </span>
        ) : null}
      </div>

      {r.notes.length ? <div className="result-note">⚠ {r.notes.join(" ")}</div> : null}

      <ReportActions data={data} />

      {r.scope_rollup?.length ? (
        <div className="result-block">
          <h3>Rollup per Scope (GHG Protocol)</h3>
          <ScopeRollup items={r.scope_rollup} />
        </div>
      ) : null}

      {r.facility_rollup?.length ? (
        <div className="result-block">
          <h3>Per fasilitas</h3>
          <div className="fac-rollup">
            {r.facility_rollup.map((f) => (
              <div className="fac-row" key={f.name}>
                <div className="fac-head">
                  <span className="fac-name">{f.name}</span>
                  <span className="fac-val mono">
                    {fmtNumber(f.co2e_kg / 1000)} <span className="bd-unit">tCO₂e</span>
                  </span>
                  <span className="fac-share mono">{(f.share * 100).toFixed(1)}%</span>
                </div>
                {f.by_scope.length ? (
                  <div className="fac-scopes">
                    {f.by_scope.map((s) => (
                      <span className="fac-scope-chip" key={s.scope}>
                        S{s.scope}: {fmtNumber(s.co2e_kg / 1000)} t
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="result-block">
        <h3>Rincian per kategori</h3>
        <BreakdownBars items={r.breakdown} />
      </div>

      {r.sensitivity && r.sensitivity.length > 1 ? (
        <div className="result-block">
          <h3>Sensitivity — sumber ketidakpastian</h3>
          <SensitivityBars items={r.sensitivity} />
        </div>
      ) : null}

      <div className="result-foot">
        <span className="mono">run: {data.run_id.slice(0, 8)}</span>
        <span>Tersimpan & dapat dihitung ulang (snapshot beku).</span>
      </div>

      <ReportPrint data={data} />
    </div>
  );
}
