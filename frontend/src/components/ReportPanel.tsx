// Ekspor laporan: tombol "Cetak/PDF" (browser Print) + unduh data.
// Laporan dirender dari CalcResponse (termasuk methodology appendix), jadi
// self-contained & jalan identik di build penuh maupun demo statis.
// - Cetak/PDF: window.print() pada dokumen tersembunyi (lihat report.css @media print).
// - Unduh: build penuh → .xlsx dari backend; statis → .csv dibuat client-side.

import { getToken } from "../lib/api";
import type { CalcResponse, MethodologyItem } from "../lib/domainTypes";
import { fmtNumber } from "../lib/format";
import { Button } from "./ui";
import "./report.css";

const STATIC = import.meta.env.VITE_STATIC === "1";

const DOMAIN_TITLE: Record<string, string> = {
  personal: "Jejak Karbon Personal",
  organizational: "GHG Accounting Organisasi",
};

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function csvCell(v: unknown): string {
  const s = v == null ? "" : String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function buildCsv(data: CalcResponse): string {
  const r = data.report;
  const lines: string[] = [];
  lines.push(["Laporan Emisi — Carbon Engine"].map(csvCell).join(","));
  lines.push(["Domain", r.domain_id].map(csvCell).join(","));
  lines.push(["Run ID", data.run_id].map(csvCell).join(","));
  lines.push(["Total kg CO2e", r.total_co2e_kg].map(csvCell).join(","));
  lines.push(["Total t CO2e", r.total_co2e_tonnes].map(csvCell).join(","));
  if (r.scope_rollup?.length) {
    lines.push("");
    lines.push(["Scope", "kg CO2e", "share %"].map(csvCell).join(","));
    for (const s of r.scope_rollup)
      lines.push([`Scope ${s.scope}`, s.co2e_kg, (s.share * 100).toFixed(2)].map(csvCell).join(","));
  }
  lines.push("");
  lines.push(["Kategori", "kg CO2e", "share %"].map(csvCell).join(","));
  for (const b of r.breakdown)
    lines.push([b.name, b.co2e_kg, (b.share * 100).toFixed(2)].map(csvCell).join(","));
  if (r.methodology?.length) {
    lines.push("");
    lines.push(["Methodology — Kategori", "Gas", "Nilai", "Unit", "Versi", "Region",
      "GWP", "Sumber", "Publisher", "Tahun", "Tier sumber", "URL"].map(csvCell).join(","));
    for (const m of r.methodology)
      lines.push([m.category_name, m.gas, m.value, m.unit, m.version, m.region, m.gwp_applied,
        m.source.name, m.source.publisher, m.source.year, m.source.credibility_tier, m.source.url]
        .map(csvCell).join(","));
  }
  return lines.join("\n");
}

export function ReportActions({ data }: { data: CalcResponse }) {
  async function exportData() {
    if (STATIC) {
      triggerDownload(new Blob([buildCsv(data)], { type: "text/csv;charset=utf-8" }),
        `laporan-${data.report.domain_id}-${data.run_id.slice(0, 8)}.csv`);
      return;
    }
    const token = getToken();
    const res = await fetch(`/api/reports/${data.run_id}.xlsx`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      alert("Gagal mengunduh laporan Excel.");
      return;
    }
    triggerDownload(await res.blob(), `laporan-${data.report.domain_id}-${data.run_id.slice(0, 8)}.xlsx`);
  }

  return (
    <div className="report-actions">
      <Button variant="ghost" onClick={() => window.print()}>Cetak / Simpan PDF</Button>
      <Button variant="ghost" onClick={exportData}>{STATIC ? "Unduh CSV" : "Unduh Excel"}</Button>
    </div>
  );
}

// Dokumen laporan untuk dicetak (tersembunyi di layar; tampil saat print).
export function ReportPrint({ data }: { data: CalcResponse }) {
  const r = data.report;
  const now = new Date().toLocaleString("id-ID");
  return (
    <div className="report-print" aria-hidden>
      <h1>Laporan Emisi — Carbon Engine</h1>
      <p className="rp-meta">
        {DOMAIN_TITLE[r.domain_id] ?? r.domain_id} · Run {data.run_id.slice(0, 8)} · {now}
      </p>

      <table className="rp-kv">
        <tbody>
          <tr><th>Total emisi</th><td>{fmtNumber(r.total_co2e_tonnes)} tCO₂e ({fmtNumber(r.total_co2e_kg)} kg)</td></tr>
          {r.uncertainty?.ci_low != null && r.uncertainty?.ci_high != null ? (
            <tr><th>95% CI</th><td>{fmtNumber(r.uncertainty.ci_low / 1000)} – {fmtNumber(r.uncertainty.ci_high / 1000)} tCO₂e</td></tr>
          ) : null}
        </tbody>
      </table>

      {r.scope_rollup?.length ? (
        <>
          <h2>Rollup per Scope (GHG Protocol)</h2>
          <table className="rp-table">
            <thead><tr><th>Scope</th><th>tCO₂e</th><th>Share</th></tr></thead>
            <tbody>
              {r.scope_rollup.map((s) => (
                <tr key={s.scope}><td>{s.label}</td><td>{fmtNumber(s.co2e_kg / 1000)}</td><td>{(s.share * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      {r.facility_rollup?.length ? (
        <>
          <h2>Per fasilitas</h2>
          <table className="rp-table">
            <thead><tr><th>Fasilitas</th><th>tCO₂e</th><th>Share</th></tr></thead>
            <tbody>
              {r.facility_rollup.map((f) => (
                <tr key={f.name}><td>{f.name}</td><td>{fmtNumber(f.co2e_kg / 1000)}</td><td>{(f.share * 100).toFixed(1)}%</td></tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      <h2>Rincian per kategori</h2>
      <table className="rp-table">
        <thead><tr><th>Kategori</th><th>kg CO₂e</th><th>Share</th></tr></thead>
        <tbody>
          {r.breakdown.map((b) => (
            <tr key={b.code}><td>{b.name}</td><td>{fmtNumber(b.co2e_kg)}</td><td>{(b.share * 100).toFixed(1)}%</td></tr>
          ))}
        </tbody>
      </table>

      {r.methodology?.length ? <MethodologyAppendix items={r.methodology} /> : null}

      {r.notes.length ? <p className="rp-note">Catatan: {r.notes.join(" ")}</p> : null}
      <p className="rp-foot">
        Hasil immutable & reproducible — tiap angka tertaut ke faktor + versi + sumber pada
        appendix metodologi. Carbon Engine.
      </p>
    </div>
  );
}

function MethodologyAppendix({ items }: { items: MethodologyItem[] }) {
  return (
    <>
      <h2>Appendix Metodologi — Faktor & Sumber</h2>
      <table className="rp-table rp-meth">
        <thead>
          <tr>
            <th>Kategori</th><th>Gas</th><th>Faktor</th><th>Unit</th><th>v</th>
            <th>Region</th><th>GWP</th><th>Sumber</th><th>Thn</th><th>Tier</th>
          </tr>
        </thead>
        <tbody>
          {items.map((m, i) => (
            <tr key={i}>
              <td>{m.category_name}</td>
              <td>{m.gas}</td>
              <td>{m.value}</td>
              <td>{m.unit}</td>
              <td>{m.version}</td>
              <td>{m.region}</td>
              <td>{m.gwp_applied}</td>
              <td>{m.source.name}{m.source.url ? ` (${m.source.url})` : ""}</td>
              <td>{m.source.year ?? "—"}</td>
              <td>{m.source.credibility_tier ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
