import type { BreakdownItem } from "../lib/domainTypes";
import { fmtNumber } from "../lib/format";
import "./charts.css";

const PALETTE = [
  "var(--c-co2)",
  "var(--c-ch4)",
  "var(--c-scope3)",
  "var(--c-n2o)",
  "var(--c-scope1)",
  "oklch(0.6 0.04 255)",
  "oklch(0.62 0.1 150)",
  "oklch(0.6 0.11 330)",
];

export function BreakdownBars({ items }: { items: BreakdownItem[] }) {
  return (
    <div className="breakdown">
      {items.map((it, i) => (
        <div className="bd-row" key={it.code} style={{ ["--i" as string]: i }}>
          <div className="bd-head">
            <span className="bd-dot" style={{ background: PALETTE[i % PALETTE.length] }} />
            <span className="bd-name">{it.name}</span>
            <span className="bd-val mono">
              {fmtNumber(it.co2e_kg)} <span className="bd-unit">kg</span>
            </span>
            <span className="bd-share mono">{(it.share * 100).toFixed(1)}%</span>
          </div>
          <div className="bd-track">
            <div
              className="bd-fill"
              style={{
                width: `${Math.max(it.share * 100, 0.5)}%`,
                background: PALETTE[i % PALETTE.length],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

interface BenchRow {
  label: string;
  value: number;
  kind: "you" | "ref";
  note?: string;
}

export function BenchmarkChart({
  youTonnes,
  benchmarks,
}: {
  youTonnes: number;
  benchmarks: Record<string, number>;
}) {
  const labels: Record<string, string> = {
    indonesia_avg: "Rata-rata Indonesia",
    world_avg: "Rata-rata dunia",
    target_2030: "Target 1.5°C (2030)",
  };
  const rows: BenchRow[] = [
    { label: "Anda", value: youTonnes, kind: "you" },
    ...Object.entries(benchmarks).map(([k, v]) => ({
      label: labels[k] ?? k,
      value: v,
      kind: "ref" as const,
    })),
  ];
  const max = Math.max(...rows.map((r) => r.value), 0.1) * 1.1;

  return (
    <div className="bench">
      {rows.map((r) => (
        <div className={`bench-row${r.kind === "you" ? " is-you" : ""}`} key={r.label}>
          <span className="bench-label">{r.label}</span>
          <div className="bench-track">
            <div className="bench-fill" style={{ width: `${(r.value / max) * 100}%` }} />
          </div>
          <span className="bench-val mono">{r.value.toFixed(2)}</span>
        </div>
      ))}
      <div className="bench-axis mono">tCO₂e / tahun</div>
    </div>
  );
}
