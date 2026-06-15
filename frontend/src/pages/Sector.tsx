import { useMemo, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import type { CalcResponse, SchemaResponse } from "../lib/domainTypes";
import type { GWPSet } from "../lib/types";
import { Button, EmptyState, Spinner } from "../components/ui";
import { BreakdownBars, SensitivityBars } from "../components/charts";
import { ReportActions, ReportPrint } from "../components/ReportPanel";
import "./calculator.css";

interface SchemaUi {
  group: string;
  unit: string;
  help?: string;
  placeholder?: string;
}

export function Sector() {
  const schema = useAsync(() => api.get<SchemaResponse>("/domains/sector/schema"), []);
  const gwps = useAsync(() => api.get<GWPSet[]>("/gwp-sets"), []);

  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [gwpName, setGwpName] = useState("AR6");
  const [method, setMethod] = useState<"analytical" | "montecarlo">("analytical");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CalcResponse | null>(null);

  const groups = useMemo(() => {
    const s = schema.data?.input_schema;
    if (!s) return [];
    const order = s["x-groups"] ?? [];
    const byGroup = new Map<string, { key: string; title: string; ui: SchemaUi }[]>();
    for (const [key, prop] of Object.entries(s.properties)) {
      if (prop.type !== "number") continue;
      const ui = (prop["x-ui"] ?? { group: "Lainnya", unit: "" }) as SchemaUi;
      const arr = byGroup.get(ui.group) ?? [];
      arr.push({ key, title: prop.title, ui });
      byGroup.set(ui.group, arr);
    }
    const ordered = [...order, ...[...byGroup.keys()].filter((g) => !order.includes(g))];
    return ordered.filter((g) => byGroup.has(g)).map((g) => ({ group: g, fields: byGroup.get(g)! }));
  }, [schema.data]);

  const hasInput = Object.values(inputs).some((v) => v !== "" && Number(v) > 0);

  async function submit() {
    setBusy(true);
    setError(null);
    const numeric: Record<string, number> = {};
    for (const [k, v] of Object.entries(inputs)) {
      if (v !== "" && !Number.isNaN(Number(v))) numeric[k] = Number(v);
    }
    try {
      const res = await api.post<CalcResponse>("/domains/sector/calculate", {
        gwp_set_name: gwpName,
        uncertainty_method: method,
        inputs: numeric,
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
          <h1>Sektor — Pertanian & Energi</h1>
          <p className="page-sub">
            Estimasi emisi sektoral dengan <strong>metode IPCC Tier</strong> (CH₄ enterik &
            N₂O manure berbasis populasi, N₂O pupuk, CH₄ sawah). Hasil bersitasi &{" "}
            <strong>reproducible</strong>.
          </p>
        </div>
      </header>

      <div className="calc-grid">
        <section className="calc-form">
          <div className="calc-context">
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

          {groups.map((g) => (
            <fieldset className="calc-group" key={g.group}>
              <legend>{g.group}</legend>
              <div className="calc-fields">
                {g.fields.map((f) => (
                  <label className="calc-field" key={f.key}>
                    <span className="calc-field-label">{f.title}</span>
                    <div className="calc-input">
                      <input type="number" min={0} step="any" inputMode="decimal"
                        placeholder={f.ui.placeholder ?? "0"}
                        value={inputs[f.key] ?? ""}
                        onChange={(e) => setInputs({ ...inputs, [f.key]: e.target.value })} />
                      <span className="calc-unit">{f.ui.unit}</span>
                    </div>
                    {f.ui.help ? <span className="calc-help">{f.ui.help}</span> : null}
                  </label>
                ))}
              </div>
            </fieldset>
          ))}

          {error ? <div className="login-error">{error}</div> : null}
          <Button variant="primary" onClick={submit} loading={busy} disabled={!hasInput}>
            Hitung Emisi
          </Button>
        </section>

        <aside className="calc-result" id="result">
          {result ? (
            <SectorResult data={result} />
          ) : (
            <div className="result-placeholder">
              <div className="rp-mark" aria-hidden>
                CO<sub>2</sub>e
              </div>
              <p>
                Hasil akan muncul di sini: total <strong>tCO₂e</strong>, rincian per kategori
                (enterik, manure, pupuk, sawah, energi), dan sumber ketidakpastian.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function SectorResult({ data }: { data: CalcResponse }) {
  const r = data.report;
  const unc = r.uncertainty;
  return (
    <div className="result">
      <div className="result-hero">
        <span className="rh-label">Total emisi sektor</span>
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
