// Pemformatan angka — presisi jujur, tanpa false-precision berlebihan.

export function fmtNumber(v: number, maxSig = 5): string {
  if (v === 0) return "0";
  const abs = Math.abs(v);
  if (abs < 1e-4 || abs >= 1e7) return v.toExponential(2);
  return v.toLocaleString("en-US", { maximumSignificantDigits: maxSig });
}

export function fmtUncertaintyPct(pct: number | null): string {
  return pct == null ? "—" : `±${pct}%`;
}

export function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("id-ID", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function gasColor(symbol: string | undefined): string {
  switch (symbol) {
    case "CO2":
      return "var(--c-co2)";
    case "CH4":
      return "var(--c-ch4)";
    case "N2O":
      return "var(--c-n2o)";
    default:
      return "var(--muted)";
  }
}
