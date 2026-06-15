import { useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import type { Category, EmissionFactor, EmissionFactorInput, FactorSource, Gas } from "../lib/types";
import { fmtDate, fmtNumber, fmtUncertaintyPct, gasColor } from "../lib/format";
import { Badge, Button, EmptyState, Spinner, TierBadge } from "../components/ui";
import { Dialog } from "../components/Dialog";
import { FactorForm } from "./FactorForm";
import "./registry.css";

function ScopeBadge({ scope }: { scope: number | null }) {
  if (!scope) return null;
  return <Badge tone={`scope${scope}` as "scope1"}>Scope {scope}</Badge>;
}

export function FactorRegistry() {
  const factors = useAsync(() => api.get<EmissionFactor[]>("/factors"), []);
  const categories = useAsync(() => api.get<Category[]>("/categories"), []);
  const gases = useAsync(() => api.get<Gas[]>("/gases"), []);
  const sources = useAsync(() => api.get<FactorSource[]>("/sources"), []);

  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("all");
  const [creating, setCreating] = useState(false);
  const [detail, setDetail] = useState<EmissionFactor | null>(null);
  const [versionOf, setVersionOf] = useState<EmissionFactor | null>(null);

  const regions = useMemo(() => {
    const set = new Set((factors.data ?? []).map((f) => f.region));
    return ["all", ...Array.from(set).sort()];
  }, [factors.data]);

  const rows = useMemo(() => {
    let list = factors.data ?? [];
    if (region !== "all") list = list.filter((f) => f.region === region);
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (f) =>
          f.category?.name.toLowerCase().includes(q) ||
          f.category?.code.toLowerCase().includes(q) ||
          f.gas?.symbol.toLowerCase().includes(q) ||
          f.source?.name.toLowerCase().includes(q)
      );
    }
    return list;
  }, [factors.data, region, query]);

  const ready = categories.data && gases.data && sources.data;

  async function createFactor(data: EmissionFactorInput) {
    await api.post("/factors", data);
    setCreating(false);
    factors.reload();
  }
  async function newVersion(data: EmissionFactorInput) {
    if (!versionOf) return;
    await api.post(`/factors/${versionOf.id}/versions`, data);
    setVersionOf(null);
    setDetail(null);
    factors.reload();
  }

  return (
    <div>
      <header className="page-head">
        <div>
          <h1>Emission Factors</h1>
          <p className="page-sub">
            Jantung sistem — multi-source, multi-region, <strong>versioned</strong>. Setiap
            hasil membekukan snapshot faktor ini, bukan referensi live.
          </p>
        </div>
        <Button variant="primary" onClick={() => setCreating(true)} disabled={!ready}>
          + Tambah Faktor
        </Button>
      </header>

      <div className="toolbar">
        <input
          className="control search"
          placeholder="Cari kategori, gas, atau sumber…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="region-tabs">
          {regions.map((r) => (
            <button
              key={r}
              className={`region-tab${r === region ? " is-active" : ""}`}
              onClick={() => setRegion(r)}
            >
              {r === "all" ? "Semua region" : r}
            </button>
          ))}
        </div>
        <span className="count">
          {rows.length} faktor aktif
        </span>
      </div>

      {factors.loading ? (
        <div className="loading-row">
          <Spinner /> Memuat faktor…
        </div>
      ) : factors.error ? (
        <EmptyState title="Gagal memuat" hint={factors.error} />
      ) : rows.length === 0 ? (
        <EmptyState title="Tidak ada faktor" hint="Sesuaikan pencarian atau tambah faktor baru." />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Kategori</th>
                <th>Gas</th>
                <th className="num">Nilai</th>
                <th>Unit</th>
                <th>Region</th>
                <th>Ketidakpastian</th>
                <th>Sumber</th>
                <th className="num">Ver</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr key={f.id} onClick={() => setDetail(f)} className="row">
                  <td>
                    <div className="cat-cell">
                      <span className="cat-name">{f.category?.name}</span>
                      <span className="cat-code mono">{f.category?.code}</span>
                    </div>
                  </td>
                  <td>
                    <span className="gas-chip" style={{ color: gasColor(f.gas?.symbol) }}>
                      <span className="gas-dot" style={{ background: gasColor(f.gas?.symbol) }} />
                      {f.gas?.symbol}
                    </span>
                  </td>
                  <td className="num mono">{fmtNumber(f.value)}</td>
                  <td className="mono unit">{f.unit}</td>
                  <td>
                    <span className="mono region-cell">{f.region}</span>
                  </td>
                  <td className="mono unc">{fmtUncertaintyPct(f.uncertainty_pct)}</td>
                  <td>
                    <div className="src-cell">
                      {f.source && <TierBadge tier={f.source.credibility_tier} />}
                      <span className="src-name">{f.source?.name}</span>
                      {(f.meta as { placeholder?: boolean })?.placeholder ? (
                        <Badge tone="warn">placeholder</Badge>
                      ) : null}
                    </div>
                  </td>
                  <td className="num mono">v{f.version}</td>
                  <td>
                    <span className="row-chevron" aria-hidden>
                      →
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create */}
      <Dialog open={creating} onClose={() => setCreating(false)} title="Tambah Faktor Emisi" width={640}>
        {ready ? (
          <FactorForm
            categories={categories.data!}
            gases={gases.data!}
            sources={sources.data!}
            onSubmit={createFactor}
            onCancel={() => setCreating(false)}
          />
        ) : null}
      </Dialog>

      {/* New version */}
      <Dialog
        open={!!versionOf}
        onClose={() => setVersionOf(null)}
        title="Versi Faktor Baru"
        width={640}
      >
        {versionOf && ready ? (
          <FactorForm
            categories={categories.data!}
            gases={gases.data!}
            sources={sources.data!}
            initial={versionOf}
            onSubmit={newVersion}
            onCancel={() => setVersionOf(null)}
          />
        ) : null}
      </Dialog>

      {/* Detail / provenance */}
      <Dialog open={!!detail} onClose={() => setDetail(null)} title="Provenance Faktor" width={620}>
        {detail ? (
          <FactorDetail
            factor={detail}
            onNewVersion={() => {
              setVersionOf(detail);
            }}
          />
        ) : null}
      </Dialog>
    </div>
  );
}

function FactorDetail({
  factor,
  onNewVersion,
}: {
  factor: EmissionFactor;
  onNewVersion: () => void;
}) {
  const versions = useAsync(
    () => api.get<EmissionFactor[]>(`/factors/${factor.id}/versions`),
    [factor.id]
  );
  const placeholder = (factor.meta as { placeholder?: boolean })?.placeholder;

  return (
    <div className="detail">
      <div className="detail-headline">
        <span className="gas-chip" style={{ color: gasColor(factor.gas?.symbol) }}>
          <span className="gas-dot" style={{ background: gasColor(factor.gas?.symbol) }} />
          {factor.gas?.symbol}
        </span>
        <span className="detail-value mono">
          {fmtNumber(factor.value)} <span className="detail-unit">{factor.unit}</span>
        </span>
      </div>

      {placeholder ? (
        <div className="placeholder-warn">
          ⚠ Nilai placeholder. Ganti dengan faktor resmi sebelum dipakai untuk publikasi.
        </div>
      ) : null}

      <dl className="prov">
        <Row k="Kategori" v={`${factor.category?.name} (${factor.category?.code})`} />
        <Row
          k="Scope / domain"
          v={
            <>
              <ScopeBadge scope={factor.category?.scope ?? null} />{" "}
              {(factor.category?.domain_applicability ?? []).join(", ")}
            </>
          }
        />
        <Row k="GWP basis" v={factor.gwp_basis ?? "per-gas (dikonversi via GWP set)"} />
        <Row k="Tier IPCC" v={factor.tier ? `Tier ${factor.tier}` : "—"} mono />
        <Row k="Ketidakpastian" v={fmtUncertaintyPct(factor.uncertainty_pct)} mono />
        {factor.dist_type ? (
          <Row k="Distribusi" v={`${factor.dist_type} ${JSON.stringify(factor.dist_params)}`} mono />
        ) : null}
        <Row k="Berlaku" v={`${fmtDate(factor.valid_from)} → ${fmtDate(factor.valid_to)}`} mono />
      </dl>

      <div className="prov-source">
        <div className="prov-source-head">
          <span className="prov-label">Sumber</span>
          {factor.source && <TierBadge tier={factor.source.credibility_tier} />}
        </div>
        <div className="prov-source-name">{factor.source?.name}</div>
        <div className="prov-source-meta">
          {factor.source?.publisher} · {factor.source?.year}
          {factor.source?.url ? (
            <>
              {" · "}
              <a href={factor.source.url} target="_blank" rel="noreferrer">
                sumber ↗
              </a>
            </>
          ) : null}
        </div>
        {factor.source?.notes ? <p className="prov-notes">{factor.source.notes}</p> : null}
      </div>

      <div className="versions">
        <span className="prov-label">Riwayat versi</span>
        {versions.loading ? (
          <Spinner />
        ) : (
          <ol className="version-list">
            {(versions.data ?? []).map((v) => (
              <li key={v.id} className={v.is_active ? "is-active" : ""}>
                <span className="mono v-num">v{v.version}</span>
                <span className="mono v-val">{fmtNumber(v.value)} {v.unit}</span>
                <span className="v-date">{fmtDate(v.valid_from)}</span>
                {v.is_active ? <Badge tone="active">aktif</Badge> : <Badge tone="inactive">ditutup</Badge>}
              </li>
            ))}
          </ol>
        )}
      </div>

      <div className="ff-actions">
        <Button variant="outline" onClick={onNewVersion}>
          Buat Versi Baru
        </Button>
      </div>
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="prov-row">
      <dt>{k}</dt>
      <dd className={mono ? "mono" : undefined}>{v}</dd>
    </div>
  );
}
