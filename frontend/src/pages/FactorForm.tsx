import { useState, type FormEvent } from "react";
import type {
  Category,
  EmissionFactor,
  EmissionFactorInput,
  FactorSource,
  Gas,
} from "../lib/types";
import { Button, Field, Input, Select } from "../components/ui";

interface Props {
  categories: Category[];
  gases: Gas[];
  sources: FactorSource[];
  initial?: EmissionFactor; // jika diisi: mode "versi baru" (identitas dikunci)
  onSubmit: (data: EmissionFactorInput) => Promise<void>;
  onCancel: () => void;
}

export function FactorForm({ categories, gases, sources, initial, onSubmit, onCancel }: Props) {
  const lockIdentity = !!initial;
  const [categoryId, setCategoryId] = useState(initial?.category_id ?? categories[0]?.id ?? "");
  const [gasId, setGasId] = useState(initial?.gas_id ?? gases[0]?.id ?? "");
  const [sourceId, setSourceId] = useState(initial?.source_id ?? sources[0]?.id ?? "");
  const [value, setValue] = useState(initial ? String(initial.value) : "");
  const cat = categories.find((c) => c.id === categoryId);
  const [unit, setUnit] = useState(
    initial?.unit ?? (cat?.default_unit ? `kgCO2e/${cat.default_unit}` : "")
  );
  const [region, setRegion] = useState(initial?.region ?? "GLOBAL");
  const [co2e, setCo2e] = useState((initial?.gwp_basis ?? "CO2e") === "CO2e");
  const [tier, setTier] = useState(initial?.tier ? String(initial.tier) : "");
  const [uncPct, setUncPct] = useState(
    initial?.uncertainty_pct != null ? String(initial.uncertainty_pct) : ""
  );
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await onSubmit({
        category_id: categoryId,
        gas_id: gasId,
        source_id: sourceId,
        value: Number(value),
        unit,
        region,
        gwp_basis: co2e ? "CO2e" : null,
        tier: tier ? Number(tier) : null,
        dist_type: null,
        dist_params: null,
        uncertainty_pct: uncPct ? Number(uncPct) : null,
        meta: null,
      });
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : "Gagal menyimpan");
      setBusy(false);
    }
  }

  return (
    <form className="ff" onSubmit={submit}>
      {lockIdentity ? (
        <p className="ff-note">
          Versi baru menutup versi aktif sebelumnya — identitas (kategori, gas, region)
          dikunci. Edit faktor = baris versi baru, bukan menimpa.
        </p>
      ) : null}

      <div className="ff-grid">
        <Field label="Kategori">
          <Select
            value={categoryId}
            disabled={lockIdentity}
            onChange={(e) => {
              setCategoryId(e.target.value);
              const c = categories.find((x) => x.id === e.target.value);
              if (c?.default_unit && !initial) setUnit(`kgCO2e/${c.default_unit}`);
            }}
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Gas">
          <Select value={gasId} disabled={lockIdentity} onChange={(e) => setGasId(e.target.value)}>
            {gases.map((g) => (
              <option key={g.id} value={g.id}>
                {g.symbol} — {g.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Nilai faktor" hint="Per unit aktivitas.">
          <Input
            type="number"
            step="any"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            required
          />
        </Field>
        <Field label="Unit" hint="mis. kgCO2e/kWh atau kgCH4/kWh">
          <Input value={unit} onChange={(e) => setUnit(e.target.value)} required />
        </Field>
        <Field label="Region" hint="ID-Jamali, ID-Sumatera, GLOBAL …">
          <Input value={region} disabled={lockIdentity} onChange={(e) => setRegion(e.target.value)} />
        </Field>
        <Field label="Sumber">
          <Select value={sourceId} onChange={(e) => setSourceId(e.target.value)}>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tier IPCC" hint="Kosongkan jika tidak relevan.">
          <Select value={tier} onChange={(e) => setTier(e.target.value)}>
            <option value="">—</option>
            <option value="1">Tier 1</option>
            <option value="2">Tier 2</option>
            <option value="3">Tier 3</option>
          </Select>
        </Field>
        <Field label="Ketidakpastian ±%" hint="Pada ~95% CI.">
          <Input
            type="number"
            step="any"
            value={uncPct}
            onChange={(e) => setUncPct(e.target.value)}
          />
        </Field>
      </div>

      <label className="ff-check">
        <input type="checkbox" checked={co2e} onChange={(e) => setCo2e(e.target.checked)} />
        <span>
          Faktor sudah dalam CO₂e (gwp_basis = CO2e). Jika tidak dicentang, engine
          mengonversi gas ke CO₂e via GWP set.
        </span>
      </label>

      {err ? <div className="login-error">{err}</div> : null}

      <div className="ff-actions">
        <Button type="button" variant="ghost" onClick={onCancel}>
          Batal
        </Button>
        <Button type="submit" variant="primary" loading={busy}>
          {lockIdentity ? "Simpan Versi Baru" : "Tambah Faktor"}
        </Button>
      </div>
    </form>
  );
}
