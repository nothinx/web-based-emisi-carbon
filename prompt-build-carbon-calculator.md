# Prompt Build — Research-Grade Multi-Domain Carbon Emission Calculator

> Copy-paste prompt ini ke Claude Code. Bangun bertahap mengikuti **Build Order**; jangan kerjakan semua domain sekaligus.

---

## 1. Konteks & Tujuan

Bangun web app untuk menghitung emisi karbon (CO₂e) yang **layak dipakai untuk penelitian**, bukan sekadar kalkulator awam. Aplikasi mendukung **4 domain** yang bisa dipilih user:

1. **Personal** — jejak karbon individu/rumah tangga
2. **Organizational** — GHG accounting korporat (GHG Protocol Scope 1/2/3)
3. **Product/LCA** — product carbon footprint (parametrik/disederhanakan)
4. **Sector** — pertanian & energi (IPCC tier methods)

Pembeda dari kalkulator biasa: **reproducibility, ketertelusuran (provenance), kuantifikasi ketidakpastian, dan faktor emisi lokal Indonesia**.

---

## 2. Prinsip Inti (Non-Negotiable)

1. **Reproducible** — setiap perhitungan harus bisa dihitung ulang dan menghasilkan angka identik kapan pun.
2. **Traceable** — setiap angka emisi bisa ditelusuri: faktor mana, versi berapa, sumber publikasi apa, GWP set apa, asumsi apa.
3. **Uncertain-aware** — emisi dilaporkan dengan estimasi ketidakpastian, bukan angka tunggal palsu-presisi.
4. **Modular** — JANGAN bikin 4 kalkulator terpisah. Satu *core* + *domain modules* yang di-plug di atasnya.
5. **Local-first factors** — utamakan faktor emisi Indonesia (grid PLN per sistem interkoneksi, data KLH) bila tersedia; faktor internasional (IPCC/DEFRA/EPA) sebagai fallback.

---

## 3. Arsitektur Tingkat Tinggi

```
┌─────────────────────────────────────────────────────────────┐
│                      DOMAIN MODULES                           │
│   Personal │ Organizational │ Product/LCA │ Sector(Tani/Energi)│
│   (masing-masing: input schema, kategori, strategy, agregasi) │
└───────────────────────────┬───────────────────────────────────┘
                            │ DomainModule contract
┌───────────────────────────▼───────────────────────────────────┐
│                          CORE                                  │
│  Factor Registry │ Calculation Engine │ GWP Service │ Units    │
│  Uncertainty Engine │ Provenance/Result Store (immutable)      │
└───────────────────────────┬───────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   REST API           IoT Ingestion        PDF/Excel Report
   (CRUD + run)       (sensor → activity)   (+ methodology appendix)
```

Tiap domain HANYA berbeda di: (a) form/input schema, (b) kategori faktor relevan, (c) strategy perhitungan, (d) cara agregasi & output. Core tidak boleh tahu detail domain.

---

## 4. Tech Stack (sudah dikunci)

| Layer | Pilihan | Alasan |
|---|---|---|
| Backend | **FastAPI** (Python) | async-friendly untuk jalur IoT ingestion, API-first |
| ORM / migrasi | **SQLAlchemy 2.x + Alembic** | versioning schema yang ketat |
| Validasi | **Pydantic v2** | schema kontrak yang kuat |
| DB | **PostgreSQL** | relasional + **JSONB** untuk input domain yang fleksibel |
| Frontend | **React + TypeScript + Vite** | UI domain-switching dinamis |
| Charting | Recharts / Plotly | tren, komposisi, CI bands |
| Form dinamis | render dari **JSON Schema** per domain | tambah field tanpa migrasi |
| Export | WeasyPrint (PDF), openpyxl (Excel) | laporan + methodology appendix |
| Auth | JWT; API key terpisah untuk ingestion | pisahkan user vs mesin |

Catatan: JANGAN pilih Django. Jalur IoT ingestion (domain utama peneliti) lebih bersih dengan FastAPI async. Factor registry CRUD dibuat sebagai UI React custom, bukan admin bawaan.

---

## 5. Data Model (Core)

Implementasikan sebagai tabel PostgreSQL via SQLAlchemy. Field minimum:

**`FactorSource`** — sumber faktor
- `id`, `name` (mis. "IPCC EFDB", "DEFRA 2024", "PLN Grid Jamali", "KLH"), `publisher`, `url`, `year`, `credibility_tier` (1=primary/official, 2=secondary), `notes`

**`Gas`**
- `id`, `symbol` (CO2, CH4, N2O, ...), `name`

**`GWPSet`** — set Global Warming Potential
- `id`, `name` (AR4 / AR5 / AR6), `horizon_years` (default 100)
- relasi `GWPValue`: (`gwp_set_id`, `gas_id`, `gwp`)

**`Category`** — kategori aktivitas, hierarkis
- `id`, `code`, `name`, `parent_id` (self-FK), `domain_applicability` (array domain), `scope` (1/2/3, nullable; relevan untuk Organizational), `default_unit`

**`EmissionFactor`** — JANTUNG sistem
- `id`, `category_id`, `gas_id`, `value`, `unit` (per-unit aktivitas), `region` (mis. ID-Jamali, GLOBAL), `source_id`, `gwp_basis` (nullable — beberapa faktor sudah dalam CO₂e), `tier` (IPCC 1/2/3, nullable)
- versioning: `version`, `valid_from`, `valid_to`, `is_active`
- uncertainty: `dist_type` (lognormal/normal/uniform/triangular), `dist_params` (JSONB), `uncertainty_pct` (nullable shorthand)
- `metadata` (JSONB)

**`Project`** — subjek penilaian / unit penelitian
- `id`, `owner_id`, `name`, `domain`, `region`, `reporting_period_start/end`, `base_year`, `gwp_set_id`, `functional_unit` (nullable, untuk LCA), `description`

**`ActivityRecord`** — data aktivitas mentah
- `id`, `project_id`, `category_id`, `amount`, `unit`, `period`, `domain_fields` (JSONB — field spesifik domain), `data_origin` (manual/import/sensor), `activity_uncertainty` (JSONB, nullable)

**`CalculationRun`** — satu eksekusi perhitungan
- `id`, `project_id`, `created_at`, `gwp_set_id`, `methodology_config` (JSONB), `uncertainty_method` (none/analytical/montecarlo), `status`

**`CalculationResult`** — IMMUTABLE, append-only
- `id`, `run_id`, `activity_record_id`, `strategy_used`
- **`factor_snapshot`** (JSONB) — bekukan: nilai faktor, unit, version, source citation lengkap, dist_params. **Hasil TIDAK BOLEH mereferensi `EmissionFactor` live.**
- `co2e_kg`, `co2e_uncertainty` (JSONB: mean, sd, ci_low, ci_high), `assumptions` (JSONB)

**`Scenario`** — untuk what-if/sensitivity
- `id`, `project_id`, `name`, `overrides` (JSONB — substitusi faktor/aktivitas)

Aturan keras: `CalculationResult` immutable. Recompute = `CalculationRun` baru. Edit faktor = versi baru (`valid_to` lama ditutup, baris baru `is_active`), bukan UPDATE in-place.

---

## 6. Calculation Engine (Strategy Pattern)

Engine tidak boleh hardcode "perkalian". Pakai strategy yang bisa di-plug:

```python
class CalcContext(Protocol):
    gwp_set: GWPSet
    region: str
    methodology_config: dict

class CalculationStrategy(Protocol):
    id: str
    def applicable(self, category: Category) -> bool: ...
    def calculate(self, activity: ActivityRecord, factor: EmissionFactor,
                  ctx: CalcContext) -> EmissionResult: ...
```

Strategy yang harus ada:
- **`MultiplyStrategy`** (default) — `co2e = amount × factor.value × gwp`. Cukup untuk Personal & mayoritas Scope 1/2 Organizational.
- **`IPCCTier2EntericStrategy`** — fermentasi enterik ternak: persamaan berbasis populasi & bobot, bukan perkalian tunggal.
- **`IPCCManureN2OStrategy`** — N₂O dari pengelolaan pupuk kandang & aplikasi pupuk.
- **`LCAProcessStrategy`** — telusuri inventory proses (parametrik untuk v1).

Engine: resolve faktor (by category + region + GWP set + period) → pilih strategy yang `applicable` → hitung → konversi gas ke CO₂e via GWP set → propagasi uncertainty → tulis `CalculationResult` immutable dengan `factor_snapshot`.

---

## 7. Domain Module Contract

```python
class DomainModule(Protocol):
    domain_id: str                      # personal/org/product/sector
    input_schema: dict                  # JSON Schema → render form di frontend
    categories: list[Category]
    def to_activities(self, raw_input: dict) -> list[ActivityRecord]: ...
    def aggregate(self, results: list[CalculationResult]) -> DomainReport: ...
    benchmarks: dict | None             # mis. rata-rata per kapita
```

`aggregate` berbeda per domain: per-kapita (Personal), rollup Scope 1/2/3 (Organizational), per functional unit (Product/LCA), per hektar/per ekor (Sector).

Frontend membaca `input_schema` tiap domain dan merender form secara dinamis — tidak ada form hardcoded per domain.

---

## 8. Spesifik Per Domain

**Personal** — kategori: listrik, transport (mobil/motor/pesawat), makanan/diet, sampah. Strategy: Multiply. Output: ton CO₂e/tahun + benchmark per kapita. (Domain validasi engine — bangun pertama.)

**Organizational** — full GHG Protocol. Scope 1 (pembakaran langsung, kendaraan), Scope 2 (listrik beli → grid factor regional), Scope 3 (15 kategori; mulai dari perjalanan dinas & transport, sisanya bertahap). Multi-fasilitas, base year, periode pelaporan. Output: rollup per scope.

**Sector (Tani/Energi)** — pertanian: N₂O pupuk, CH₄ fermentasi enterik & manure, LULUCF (IPCC Tier 1/2/3). Energi: grid factor, fuel combustion. **Sediakan endpoint IoT ingestion** agar data sensor (energi real-time, dsb.) jadi `ActivityRecord` otomatis dengan `data_origin=sensor`.

**Product/LCA** — functional unit, bill of materials, batas cradle-to-gate/grave. **v1 parametrik** (faktor per bahan/proses), bukan integrasi database LCA komersial. **Dokumentasikan penyederhanaan ini sebagai limitation** di laporan.

---

## 9. Uncertainty

- Schema faktor membawa info distribusi sejak awal (`dist_type` + `dist_params`) — meski belum dipakai, supaya tidak retrofit nanti.
- **Phase awal**: propagasi analitis (Gaussian error propagation; kombinasi relative-error untuk produk).
- **Phase lanjut**: Monte Carlo — sampling distribusi faktor + aktivitas, N iterasi (default 10.000), laporkan mean & 95% CI.
- Hasil selalu disimpan dengan rentang ketidakpastian, bukan angka tunggal.

---

## 10. Provenance & Reproducibility (wajib)

- `CalculationResult` membekukan `factor_snapshot` lengkap — recompute deterministik.
- Setiap hasil bisa di-trace ke: versi faktor, sumber publikasi + URL + tahun, GWP set, tier metodologi, asumsi.
- Edit faktor = baris versi baru, bukan overwrite.
- Export laporan menyertakan **methodology appendix**: daftar semua faktor + sumber + versi + asumsi yang dipakai, agar dapat dipertahankan secara akademik.

---

## 11. Factor Registry & Sourcing

- Multi-source, multi-region, versioned (lihat schema §5).
- Sediakan **CRUD UI** + **seed loader** dari CSV/JSON.
- Sumber awal: IPCC EFDB, DEFRA, EPA (generik); **faktor lokal Indonesia diprioritaskan** (grid PLN per sistem interkoneksi, data KLH).
- JANGAN hardcode nilai faktor di kode — semua faktor adalah **data** di DB dengan sitasi sumber. Sediakan beberapa faktor contoh sebagai seed, tandai `credibility_tier` & sumbernya.
- Sadari: sourcing & validasi faktor adalah pekerjaan tersendiri yang berlanjut, bukan sekali jadi.

---

## 12. API Surface (sketch)

```
POST   /factors                 # tambah faktor (buat versi baru)
GET    /factors?category&region # query faktor aktif
GET    /factors/{id}/versions   # riwayat versi
CRUD   /projects
CRUD   /projects/{id}/activities
POST   /projects/{id}/calculate # buat CalculationRun → results
GET    /runs/{id}/results       # hasil immutable + provenance
POST   /ingest                  # IoT/sensor → ActivityRecord (API key auth)
POST   /projects/{id}/scenarios # what-if
GET    /reports/{run_id}.pdf    # laporan + methodology appendix
GET    /reports/{run_id}.xlsx
```

---

## 13. Build Order (kerjakan BERURUTAN)

- **Phase 0 — Core scaffolding**: data model, migrasi, Factor Registry + CRUD UI, GWP service, unit conversion, `MultiplyStrategy`, engine + `CalculationResult` immutable dengan snapshot. Seed beberapa faktor contoh.
- **Phase 1 — Personal**: domain modul paling sederhana untuk memvalidasi engine end-to-end + visualisasi dasar.
- **Phase 2 — Organizational**: Scope 1/2/3, multi-fasilitas, base year, laporan PDF/Excel + methodology appendix.
- **Phase 3 — Uncertainty + Scenario**: analitis → Monte Carlo, sensitivity analysis.
- **Phase 4 — Sector (Tani/Energi)**: IPCC tier strategies + endpoint IoT ingestion.
- **Phase 5 — Product/LCA**: parametrik, dengan limitation terdokumentasi.

Selesaikan & uji tiap phase sebelum lanjut. Setiap phase harus punya test untuk reproducibility (recompute → angka identik).

---

## 14. Fitur Khusus Penelitian

- Reproducible runs dengan frozen snapshot.
- Methodology transparency di setiap export.
- Scenario / what-if & sensitivity analysis.
- Import data (CSV) + ingestion sensor.
- Pelaporan uncertainty dengan confidence interval.
- Riwayat versi faktor yang bisa diaudit.

---

## 15. Guardrails — JANGAN

- Jangan bikin 4 kalkulator terpisah; satu core + modules.
- Jangan UPDATE faktor in-place; selalu versi baru.
- Jangan mereferensi faktor live dari `CalculationResult`; pakai snapshot.
- Jangan hardcode nilai faktor di source code; faktor = data + sitasi.
- Jangan laporkan angka tunggal tanpa konteks ketidakpastian.
- Jangan over-scope: utamakan kedalaman & kebenaran metodologi di Personal + Organizational + Sector sebelum mengejar LCA penuh.
- Jangan klaim akurasi LCA penuh; v1 parametrik adalah limitation yang harus dinyatakan.

---

## 16. Struktur Proyek (saran)

```
backend/
  app/
    core/          # engine, gwp, units, uncertainty, provenance
    factors/       # registry, models, seed loader
    domains/       # personal/ org/ product/ sector/ (tiap modul: schema, strategy, aggregate)
    api/           # routers: factors, projects, activities, calculate, ingest, reports
    models/        # SQLAlchemy
    schemas/       # Pydantic
  alembic/
  tests/           # WAJIB ada test reproducibility
frontend/
  src/
    domains/       # form dinamis dari JSON Schema
    factors/       # CRUD UI
    results/       # chart, provenance viewer, CI bands
docs/
  methodology.md   # catat sumber faktor, asumsi, batasan
```

---

## 17. Instruksi Eksekusi untuk Claude Code

1. Mulai dari **Phase 0**: scaffold backend (FastAPI + SQLAlchemy + Alembic + Postgres) dan implementasikan data model §5 lengkap dengan migrasi.
2. Implementasikan engine §6 + provenance §10 + `MultiplyStrategy`, dengan test reproducibility.
3. Buat Factor Registry + CRUD UI + seed loader (§11). Sediakan ~10–20 faktor contoh dengan sitasi sumber (tandai mana yang placeholder yang harus diganti faktor resmi).
4. Lanjut **Phase 1 (Personal)** end-to-end (backend + frontend dinamis dari JSON Schema).
5. Berhenti di akhir tiap phase, ringkas apa yang dibangun, dan tunggu konfirmasi sebelum phase berikutnya.
6. Tulis `docs/methodology.md` seiring jalan: setiap faktor, sumber, asumsi, dan batasan dicatat.

Komunikasi & komentar kode: Bahasa Indonesia, istilah teknis dibiarkan dalam bahasa Inggris. Code-first, tanpa basa-basi.
