# Methodology — Carbon Emission Engine

Dokumen ini dijaga **seiring jalan**: setiap faktor, sumber, asumsi, dan batasan
dicatat agar hasil dapat dipertahankan secara akademik. Versi: Phase 2b (export laporan).

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
  Region dapat ditentukan **per aktivitas** lewat `domain_fields.region` (mis. tiap
  fasilitas Organizational punya grid berbeda); jika tidak ada, dipakai region proyek.
- Filter masa berlaku faktor (`valid_from`/`valid_to`) memakai akhir
  `reporting_period_end`; bila kosong, jatuh ke akhir `base_year` proyek (relevan
  untuk inventarisasi Organizational per base year).

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

## 5b. Domain (Phase 1–2)

### Personal (Phase 1)
Input tahunan (bulanan ×12, mingguan ×52) → aktivitas; strategy Multiply. Output:
total tCO₂e/tahun, breakdown per kategori, perbandingan benchmark per-kapita
(indikatif: rata-rata Indonesia 2.3, dunia 4.7, target 2030 ~2.0 — perlu sitasi resmi).

### Organizational (Phase 2) — GHG Protocol Corporate
Mengikuti **GHG Protocol Corporate Standard**: emisi dikelompokkan ke
**Scope 1/2/3**. Scope tiap hasil ditentukan dari `category.scope` pada snapshot beku
(traceable, bukan dihardcode di kode domain).

- **Scope 1** (emisi langsung): `natural_gas`, `diesel_stationary`, `lpg` (pembakaran
  stasioner). Faktor `natural_gas` per-gas (CO₂+CH₄+N₂O) → dikonversi via GWP set.
- **Scope 2** (energi tidak langsung): `elec_grid` — **faktor grid PLN regional per
  fasilitas** (ID-Jamali 0.87, ID-Sumatera 1.18 kgCO₂e/kWh; placeholder).
- **Scope 3** (rantai nilai): `business_travel_air` & `waste_landfill` — level
  organisasi (lintas-fasilitas). **Baru sebagian** dari 15 kategori GHG Protocol.

Fitur: **multi-fasilitas** (region grid sendiri per fasilitas), **base year**
(jadi acuan masa-berlaku faktor bila periode pelaporan kosong). Output: rollup per
scope + rollup per fasilitas (+ rincian per scope) + breakdown per kategori.
Agregasi ketidakpastian sama seperti Personal (kombinasi sd² antar hasil).

## 5c. Pelaporan & Methodology Appendix (Phase 2b)

Setiap report domain membawa **`methodology`**: daftar faktor unik yang dipakai
(dedup per `factor_id`/identitas+versi) lengkap dengan sitasi — nilai, unit, versi,
region, GWP diterapkan, tier, dan sumber (nama, publisher, tahun, URL, credibility
tier). Dibangun dari `factor_snapshot` beku (`app/domains/base.build_methodology`),
sehingga laporan **self-contained & dapat dipertahankan akademik** tanpa query faktor
live, dan jalan identik di demo statis.

- **Excel** (`GET /reports/{run_id}.xlsx`, openpyxl): 3 sheet — Ringkasan (konteks +
  rollup scope), Hasil (per aktivitas immutable), Methodology (faktor + sumber).
- **PDF**: lewat **laporan HTML cetak** di frontend (tombol "Cetak / Simpan PDF" →
  `window.print()`; lihat `components/ReportPanel.tsx` + `report.css`). Dipilih
  ketimbang WeasyPrint karena WeasyPrint butuh native lib GTK/Pango yang **gagal di
  env Windows ini** — pendekatan HTML-print tanpa native lib & otomatis parity dengan
  demo statis (yang tak punya backend). Demo statis mengunduh **CSV** (client-side)
  sebagai ganti `.xlsx`.

## 6. Batasan (Limitations)

- **Faktor grid Indonesia adalah placeholder** — ganti dengan faktor resmi
  (Ditjen Gatrik/KLHK) per sistem interkoneksi & tahun.
- **Uncertainty Phase 0 hanya analitis**; korelasi antar-input belum dimodelkan.
  Monte Carlo (Phase 3) akan menangani distribusi penuh.
- **Belum ada uncertainty aktivitas** dalam perhitungan (skema sudah disiapkan di
  `ActivityRecord.activity_uncertainty`).
- **DEFRA dipakai sebagai fallback** untuk konteks Indonesia — sah untuk faktor
  generik (kendaraan, LPG), kurang ideal untuk yang sangat lokal.
- **Scope 3 Organizational baru sebagian** (perjalanan dinas udara & limbah TPA);
  13 kategori GHG Protocol lainnya menyusul bertahap.
- **PDF tidak digenerate server-side** — memakai cetak HTML browser (Save as PDF).
  Untuk PDF otomatis di pipeline (mis. batch/headless), pertimbangkan headless Chrome
  atau install runtime GTK agar WeasyPrint jalan; di luar lingkup env saat ini.
- Sector (IPCC Tier) & Product/LCA menyusul di Phase 4/5. LCA v1 akan **parametrik**
  dan dinyatakan sebagai limitation, bukan klaim akurasi LCA penuh.

## 7. Riwayat
- **Phase 0** — core scaffolding: data model, engine + MultiplyStrategy,
  provenance/immutability, factor registry + CRUD UI, seed 15 faktor contoh,
  uji reproducibility.
- **Phase 1** — domain Personal end-to-end: form dinamis dari JSON Schema,
  agregasi per-kapita + benchmark, visualisasi breakdown.
- **Phase 2a** — domain Organizational (GHG Protocol): Scope 1/2/3, multi-fasilitas
  dengan grid regional per fasilitas, base year, rollup per scope & per fasilitas,
  region per-aktivitas di engine, port ke build statis. Uji reproducibility +
  rollup scope.
- **Phase 2b** — pelaporan & methodology appendix: `methodology` di tiap report
  (faktor + sitasi dari snapshot), export Excel `/reports/{run_id}.xlsx` (openpyxl,
  3 sheet), laporan HTML cetak (browser Print→PDF) + unduh CSV di demo statis.
  24 backend test (+4 report).
