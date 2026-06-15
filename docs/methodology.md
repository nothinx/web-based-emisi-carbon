# Methodology — Carbon Emission Engine

Dokumen ini dijaga **seiring jalan**: setiap faktor, sumber, asumsi, dan batasan
dicatat agar hasil dapat dipertahankan secara akademik. Versi: Phase 0.

## 1. Prinsip

- **Reproducible** — setiap `CalculationResult` membekukan `factor_snapshot`
  (nilai faktor, versi, unit, sitasi sumber, GWP yang diterapkan). Recompute dari
  snapshot menghasilkan angka identik tanpa menyentuh faktor live.
- **Traceable** — tiap angka tertaut ke: faktor + versi, sumber publikasi + URL +
  tahun, GWP set + horizon, tier IPCC, dan asumsi (disimpan di `assumptions`).
- **Uncertain-aware** — hasil disimpan dengan rentang (`co2e_uncertainty`: mean, sd,
  ci_low, ci_high), bukan angka tunggal.
- **Versioned** — edit faktor = baris versi baru (`valid_to` lama ditutup,
  `is_active=False`); tidak ada UPDATE in-place.

## 2. GWP Sets

GWP-100. Sumber nilai: **IPCC AR6 WG1 Ch.7**. Set tersedia: AR6, AR5, AR4.

| Gas | AR6 | AR5 | AR4 |
|-----|----:|----:|----:|
| CO₂ | 1 | 1 | 1 |
| CH₄ | 27.9 | 28 | 25 |
| N₂O | 273 | 265 | 298 |

Catatan: nilai CH₄ AR6 yang dipakai adalah varian non-fossil/umum (27.9). Untuk
metana fosil, AR6 mencantumkan ~29.8 — pertimbangkan menambah faktor terpisah bila
diperlukan ketelitian sumber emisi.

## 3. Engine & Strategy

- **MultiplyStrategy** (Phase 0): `co2e = amount × factor.value × GWP`.
  - Unit aktivitas dikonversi ke unit penyebut faktor (mis. MWh → kWh) sebelum
    perkalian (lihat `app/core/units.py`, konversi berbasis dimensi).
  - Jika `gwp_basis = "CO2e"`, faktor sudah dalam CO₂e dan GWP tidak diterapkan
    (GWP_applied = 1).
  - Jika `gwp_basis = null` (faktor per-gas, mis. kgCH₄/kWh), engine mengonversi ke
    CO₂e via GWP set terpilih.
- Resolusi faktor: per `(kategori, region)` dengan **fallback GLOBAL** bila faktor
  regional tidak ada; satu faktor per gas (region spesifik mengalahkan GLOBAL).
  Filter masa berlaku memakai `reporting_period_end` proyek bila ada.

## 4. Uncertainty (Phase awal: analitis)

Propagasi Gaussian untuk perkalian: relative-errors dikombinasikan kuadrat
(`(sd/mean)² = Σ (sdᵢ/meanᵢ)²`), 95% CI ≈ ±1.96·sd. Sumber relative-sd:
`uncertainty_pct` (ditafsir sebagai ±% pada 95% CI) atau `dist_type` + `dist_params`
(lognormal via gsd, normal, uniform, triangular). **Monte Carlo menyusul di Phase 3.**

## 5. Faktor Contoh (Seed Phase 0)

> ⚠️ Faktor bertanda **PLACEHOLDER** adalah nilai indikatif dan **wajib diganti**
> dengan faktor resmi terbaru sebelum dipakai untuk publikasi.

### Sumber
| Key | Sumber | Tier | Catatan |
|-----|--------|:----:|---------|
| pln_klh | PLN / KLHK Grid Emission Factor (Indonesia) | 1 | PLACEHOLDER nilai grid per sistem interkoneksi |
| defra_2024 | UK DEFRA/BEIS GHG Conversion Factors 2024 | 2 | Fallback internasional |
| poore_nemecek_2018 | Poore & Nemecek (2018), Science 360:987 | 1 | LCA pangan, median cradle-to-retail |
| ipcc_ar6 | IPCC AR6 WG1 Ch.7 | 1 | Sumber GWP |
| iea_2023 | IEA World Average Electricity EF | 2 | PLACEHOLDER fallback GLOBAL |

### Faktor (aktif)
| Kategori | Gas | Nilai | Unit | Region | Sumber | Unc. | Catatan |
|----------|-----|------:|------|--------|--------|-----:|---------|
| elec_grid | CO₂ | 0.87 | kgCO2e/kWh | ID-Jamali | pln_klh | ±10% | PLACEHOLDER (Jawa-Madura-Bali) |
| elec_grid | CO₂ | 1.18 | kgCO2e/kWh | ID-Sumatera | pln_klh | ±12% | PLACEHOLDER |
| elec_grid | CO₂ | 0.475 | kgCO2e/kWh | GLOBAL | iea_2023 | ±15% | PLACEHOLDER |
| car_petrol | CO₂ | 0.17048 | kgCO2e/km | GLOBAL | defra_2024 | ±5% | average car, petrol |
| motorcycle | CO₂ | 0.10086 | kgCO2e/km | GLOBAL | defra_2024 | ±10% | |
| flight_domestic | CO₂ | 0.2443 | kgCO2e/pkm | GLOBAL | defra_2024 | ±8% | incl. RF uplift |
| food_beef | CO₂ | 99.48 | kgCO2e/kg | GLOBAL | poore_nemecek_2018 | lognormal gsd=1.6 | |
| food_chicken | CO₂ | 9.87 | kgCO2e/kg | GLOBAL | poore_nemecek_2018 | lognormal gsd=1.4 | |
| waste_landfill | CO₂ | 0.45867 | kgCO2e/kg | GLOBAL | defra_2024 | ±20% | PLACEHOLDER, mixed MSW |
| lpg | CO₂ | 2.93896 | kgCO2e/kg | GLOBAL | defra_2024 | ±4% | |
| diesel_stationary | CO₂ | 2.66155 | kgCO2e/L | GLOBAL | defra_2024 | ±4% | |
| business_travel_air | CO₂ | 0.158 | kgCO2e/pkm | GLOBAL | defra_2024 | ±8% | |
| natural_gas | CO₂ | 0.18316 | kgCO2/kWh | GLOBAL | defra_2024 | ±3% | per-gas (GWP=1) |
| natural_gas | CH₄ | 0.000256 | kgCH4/kWh | GLOBAL | defra_2024 | ±50% | per-gas → ×GWP |
| natural_gas | N₂O | 0.0000307 | kgN2O/kWh | GLOBAL | defra_2024 | ±50% | per-gas → ×GWP |

## 6. Batasan (Limitations)

- **Faktor grid Indonesia adalah placeholder** — ganti dengan faktor resmi
  (Ditjen Gatrik/KLHK) per sistem interkoneksi & tahun.
- **Uncertainty Phase 0 hanya analitis**; korelasi antar-input belum dimodelkan.
  Monte Carlo (Phase 3) akan menangani distribusi penuh.
- **Belum ada uncertainty aktivitas** dalam perhitungan (skema sudah disiapkan di
  `ActivityRecord.activity_uncertainty`).
- **DEFRA dipakai sebagai fallback** untuk konteks Indonesia — sah untuk faktor
  generik (kendaraan, LPG), kurang ideal untuk yang sangat lokal.
- Domain Organizational (Scope 1/2/3 penuh), Sector (IPCC Tier), dan Product/LCA
  menyusul di Phase 2/4/5. LCA v1 akan **parametrik** dan dinyatakan sebagai
  limitation, bukan klaim akurasi LCA penuh.

## 7. Riwayat
- **Phase 0** — core scaffolding: data model, engine + MultiplyStrategy,
  provenance/immutability, factor registry + CRUD UI, seed 15 faktor contoh,
  uji reproducibility.
