import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import type { Category, FactorSource, GWPSet } from "../lib/types";
import { Badge, EmptyState, Spinner, TierBadge } from "../components/ui";
import "./registry.css";

function PageHead({ title, sub }: { title: string; sub: string }) {
  return (
    <header className="page-head">
      <div>
        <h1>{title}</h1>
        <p className="page-sub">{sub}</p>
      </div>
    </header>
  );
}

export function SourcesPage() {
  const { data, loading, error } = useAsync(() => api.get<FactorSource[]>("/sources"), []);
  return (
    <div>
      <PageHead title="Sources" sub="Sumber faktor & sitasi. Tier 1 = primary/official, Tier 2 = secondary." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <EmptyState title="Gagal memuat" hint={error} />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Nama</th>
                <th>Publisher</th>
                <th className="num">Tahun</th>
                <th>Tier</th>
                <th>Tautan</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((s) => (
                <tr key={s.id}>
                  <td>
                    <div className="cat-cell">
                      <span className="cat-name">{s.name}</span>
                      {s.notes ? <span className="cat-code">{s.notes}</span> : null}
                    </div>
                  </td>
                  <td>{s.publisher ?? "—"}</td>
                  <td className="num mono">{s.year ?? "—"}</td>
                  <td>
                    <TierBadge tier={s.credibility_tier} />
                  </td>
                  <td>
                    {s.url ? (
                      <a href={s.url} target="_blank" rel="noreferrer">
                        ↗
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function CategoriesPage() {
  const { data, loading, error } = useAsync(() => api.get<Category[]>("/categories"), []);
  return (
    <div>
      <PageHead title="Categories" sub="Kategori aktivitas, hierarkis. Scope relevan untuk domain Organizational." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <EmptyState title="Gagal memuat" hint={error} />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Kode</th>
                <th>Nama</th>
                <th>Domain</th>
                <th>Scope</th>
                <th>Unit default</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((c) => (
                <tr key={c.id}>
                  <td className="mono">{c.code}</td>
                  <td>{c.name}</td>
                  <td className="mono region-cell">{c.domain_applicability.join(", ")}</td>
                  <td>{c.scope ? <Badge tone={`scope${c.scope}` as "scope1"}>Scope {c.scope}</Badge> : "—"}</td>
                  <td className="mono unit">{c.default_unit ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function GWPPage() {
  const { data, loading, error } = useAsync(() => api.get<GWPSet[]>("/gwp-sets"), []);
  return (
    <div>
      <PageHead title="GWP Sets" sub="Set Global Warming Potential. Pilihan set menentukan konversi gas → CO₂e per run." />
      {loading ? (
        <Spinner />
      ) : error ? (
        <EmptyState title="Gagal memuat" hint={error} />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Set</th>
                <th className="num">Horizon</th>
                <th>Catatan</th>
              </tr>
            </thead>
            <tbody>
              {(data ?? []).map((g) => (
                <tr key={g.id}>
                  <td className="mono">
                    <strong>{g.name}</strong>
                  </td>
                  <td className="num mono">{g.horizon_years} thn</td>
                  <td className="region-cell">{g.notes ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
