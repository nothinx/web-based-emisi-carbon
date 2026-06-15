# Methodology — Carbon Emission Engine

Dokumen ini dijaga **seiring jalan**: setiap faktor, sumber, asumsi, dan batasan
dicatat agar hasil dapat dipertahankan secara akademik. Versi: Phase 4 (Sector + IoT).

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
(lognormal via gsd, normal, uniform, triangular).

**Monte Carlo (Phase 3)** — `app/core/uncertainty.monte_carlo_total`: tiap komponen
(hasil per aktivitas/gas) disampel `N` iterasi (default 10.000). Lognormal (gsd) disampel
multiplikatif `exp(σ·Z)`, σ=ln(gsd) — menjaga sifat asimetris yang jadi alasan utama MC;
distribusi lain memakai pengali normal dari relative-sd (clip ≥0). Komponen diasumsikan
**independen** (sama seperti analitis). RNG **di-seed** (default 12345) → MC reproducible
(seed sama = angka identik). Dilaporkan: mean, sd, 95% CI (persentil 2.5/97.5), median.
Catatan: build statis memakai PRNG berbeda (mulberry32) — reproducible per-seed & ekuivalen
statistik, tapi sample-path tak identik dengan numpy backend (estimasi titik tetap sama).

**Sensitivity** — kontribusi tiap kategori ke **varians total** (share sdᵢ²/Σsd²),
menunjukkan faktor mana yang paling menentukan ketidakpastian (`build_sensitivity`).

**Scenario / what-if** — `POST /projects/{id}/scenarios/{sid}/run`: hitung baseline (run
immutable) lalu terapkan `overrides` (`factor_scale`/`activity_scale` per kategori,
multiplikatif terhadap co2e) → perbandingan baseline vs skenario + delta per kategori.
Proyeksi analitis di atas baseline; tak menyentuh faktor live.

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
| enteric_cattle | CH₄ | 68 | kgCH4/head | GLOBAL | ipcc_2019 | ±30% | PLACEHOLDER EF Tier 1/ekor/thn (sapi perah) |
| manure_cattle | N₂O | 0.005 | kgN2O-N/kgN | GLOBAL | ipcc_2019 | ±50% | PLACEHOLDER EF3; Nex=60, MS=1.0 (meta) |
| fert_synthetic_n | N₂O | 0.015714 | kgN2O/kgN | GLOBAL | ipcc_2019 | ±60% | EF1 0.01 ×44/28 (N₂O langsung Tier 1) |
| rice_cultivation | CH₄ | 143 | kgCH4/ha | GLOBAL | ipcc_2019 | ±50% | PLACEHOLDER Tier 1/ha/musim |

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

### Sector (Phase 4) — Pertanian & Energi (IPCC tier)
Strategy pattern menambah metode IPCC (bukan perkalian tunggal), dipilih per kategori:

- **CH₄ fermentasi enterik** (`ipcc.enteric.v2`, kategori `enteric_*`): Tier 1 pakai
  `factor.value` (EF kg CH₄/ekor/thn); **Tier 2** bila `domain_fields` memberi gross
  energy & Ym: `EF = GE × (Ym/100) × 365 / 55.65`. CH₄ = populasi × EF → CO₂e via GWP.
- **N₂O manure** (`ipcc.manure_n2o.v1`, kategori `manure_*`, Tier 1):
  `N₂O = populasi × Nex × MS × EF3 × 44/28`. Nex/MS dari meta faktor atau domain_fields,
  EF3 = `factor.value`.
- **N₂O pupuk sintetis** & **CH₄ sawah**: MultiplyStrategy dgn faktor ber-unit
  `kgN2O/kgN` (sudah termasuk 44/28) dan `kgCH4/ha`.
- **Energi**: reuse faktor `elec_grid` & `diesel_stationary`.

Satu input populasi sapi → dua aktivitas (enterik + manure). Parameter Tier disimpan
sebagai meta faktor (bersitasi IPCC 2019) & terekam di `assumptions` hasil (reproducible).

**IoT ingestion** — `POST /ingest` (satu) & `POST /ingest/batch` (stream, ≤5000 reading,
satu transaksi), auth **API key** terpisah (mesin). Sensor → `ActivityRecord`
(`data_origin=sensor`, `sensor_id` di domain_fields) pada project target; lalu masuk
run kalkulasi seperti data manual.

## 6. Batasan (Limitations)

- **Faktor grid Indonesia adalah placeholder** — ganti dengan faktor resmi
  (Ditjen Gatrik/KLHK) per sistem interkoneksi & tahun.
- **Korelasi antar-input belum dimodelkan** (analitis & Monte Carlo sama-sama
  mengasumsikan komponen independen). Kovarians faktor menyusul bila perlu.
- **Belum ada uncertainty aktivitas** dalam perhitungan (skema sudah disiapkan di
  `ActivityRecord.activity_uncertainty`).
- **DEFRA dipakai sebagai fallback** untuk konteks Indonesia — sah untuk faktor
  generik (kendaraan, LPG), kurang ideal untuk yang sangat lokal.
- **Scope 3 Organizational baru sebagian** (perjalanan dinas udara & limbah TPA);
  13 kategori GHG Protocol lainnya menyusul bertahap.
- **PDF tidak digenerate server-side** — memakai cetak HTML browser (Save as PDF).
  Untuk PDF otomatis di pipeline (mis. batch/headless), pertimbangkan headless Chrome
  atau install runtime GTK agar WeasyPrint jalan; di luar lingkup env saat ini.
- **Sector mayoritas Tier 1** dgn faktor default/placeholder (EF enterik, EF3 manure,
  CH₄ sawah). **LULUCF belum** dimodelkan. Tier 2/3 & faktor lokal Indonesia menyusul.
- Product/LCA menyusul di Phase 5. LCA v1 akan **parametrik** dan dinyatakan sebagai
  limitation, bukan klaim akurasi LCA penuh.

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
- **Phase 3** — uncertainty + scenario: Monte Carlo (`monte_carlo_total`, seeded,
  default 10k iter) di domain calculate (toggle Analitis/Monte Carlo di UI), sensitivity
  (share-varians per kategori), scenario what-if (`/scenarios/{sid}/run`). Port MC
  (mulberry32) + sensitivity ke build statis. 30 backend test (+6 phase 3).
- **Phase 4** — Sector (Tani/Energi): strategy IPCC enterik CH₄ (Tier 1/2) & manure
  N₂O (Tier 1), pupuk N₂O & sawah CH₄ (multiply), energi reuse; domain Sector + UI;
  IoT ingestion batch (`/ingest/batch`). Port ke build statis. 36 backend test (+6).
