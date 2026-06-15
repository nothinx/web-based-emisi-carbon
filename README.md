<div align="center">

# 🌍 Carbon Emission Engine

### Kalkulator emisi karbon (CO₂e) multi-domain tingkat penelitian — bukan sekadar kalkulator awam

**Reproducible · Traceable · Uncertainty-aware · Faktor lokal Indonesia**

[![Demo Live](https://img.shields.io/badge/▶_Demo_Live-buka_di_browser-2ea44f?style=for-the-badge)](https://nothinx.github.io/web-based-emisi-carbon/)
[![Deploy](https://github.com/nothinx/web-based-emisi-carbon/actions/workflows/deploy.yml/badge.svg)](https://github.com/nothinx/web-based-emisi-carbon/actions/workflows/deploy.yml)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![Tests](https://img.shields.io/badge/tests-40_passed-2ea44f)
![Status](https://img.shields.io/badge/fase_0–5-selesai-success)

</div>

---

## 🪧 Apa ini, dalam bahasa sederhana?

Setiap aktivitas kita — menyalakan lampu, naik kendaraan, makan daging, memproduksi
barang — melepaskan **gas rumah kaca** yang diukur dalam **kg CO₂e** (setara karbon
dioksida). Aplikasi ini menghitung jejak karbon itu untuk **empat skala berbeda** dalam
satu alat:

> 🧍 **Diri / rumah tangga** &nbsp;·&nbsp; 🏢 **Perusahaan** &nbsp;·&nbsp; 🌾 **Sektor pertanian & energi** &nbsp;·&nbsp; 📦 **Produk**

Bedanya dengan kalkulator karbon biasa di internet: di sini setiap angka **bisa
dipertanggungjawabkan secara ilmiah**. Anda selalu tahu *dari faktor apa, sumber publikasi
mana, versi berapa, dan seberapa besar ketidakpastiannya* — sehingga hasilnya layak dipakai
untuk **penelitian, skripsi, laporan keberlanjutan, atau audit**, bukan sekadar angka kira-kira.

### 👉 Coba langsung tanpa instal apa pun

**[https://nothinx.github.io/web-based-emisi-carbon/](https://nothinx.github.io/web-based-emisi-carbon/)**

Versi demo berjalan **sepenuhnya di browser** (engine perhitungan diport ke TypeScript).
Buka tautannya, langsung pakai — tanpa login, tanpa server.

---

## ✨ Yang membuatnya berbeda

| Prinsip | Artinya buat Anda |
|---|---|
| 🔁 **Reproducible** | Hitung ulang kapan pun → **angka identik**. Tiap hasil membekukan *snapshot* faktor (tidak ikut berubah meski faktor diperbarui). |
| 🔎 **Traceable** | Tiap angka tertaut ke faktor + versi + **sumber publikasi (URL, tahun)** + GWP set + asumsi. |
| 📊 **Uncertainty-aware** | Hasil dilaporkan dengan **rentang ketidakpastian (95% CI)**, bukan satu angka palsu-presisi. Tersedia **Monte Carlo**. |
| 🇮🇩 **Local-first** | Memprioritaskan faktor emisi Indonesia (grid PLN per sistem interkoneksi); internasional (IPCC/DEFRA/EPA) sebagai fallback. |
| 🧩 **Satu engine, banyak domain** | Bukan 4 kalkulator terpisah — satu *core* + *domain modules* yang berbagi mesin yang sama. |

---

## 🧮 Empat domain (dijelaskan sederhana)

<table>
<tr>
<td width="50%" valign="top">

### 🧍 Personal
Jejak karbon individu/rumah tangga: listrik, transport, makanan, sampah.
**Output:** ton CO₂e/tahun + perbandingan dengan rata-rata per kapita.

</td>
<td width="50%" valign="top">

### 🏢 Organizational (GHG Protocol)
Akuntansi karbon perusahaan: **Scope 1 / 2 / 3**, multi-fasilitas (tiap pabrik
pakai faktor grid daerahnya), *base year*.
**Output:** rollup per scope & per fasilitas + **laporan Excel/PDF**.

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🌾 Sector (Tani & Energi)
Metode **IPCC Tier**: CH₄ fermentasi enterik & N₂O kotoran ternak (berbasis populasi),
N₂O pupuk, CH₄ sawah, energi. Plus jalur **IoT ingestion** (data sensor → otomatis).

</td>
<td width="50%" valign="top">

### 📦 Product / LCA
*Product carbon footprint* **parametrik**: bill-of-materials (baja, plastik, dst.) +
energi + transport, dinormalisasi per **functional unit**. *(v1 disederhanakan — dinyatakan
sebagai limitation.)*

</td>
</tr>
</table>

---

## 🚀 Fitur utama

- ⚙️ **Calculation engine** dengan *Strategy Pattern* — bukan perkalian hardcoded; mendukung metode IPCC Tier (enterik, manure).
- 🗂️ **Factor Registry** ber-versi (CRUD UI) — faktor = **data + sitasi**, tidak pernah ditimpa (edit = versi baru).
- 🎲 **Monte Carlo** (seeded → reproducible) + propagasi analitis + **analisis sensitivitas**.
- 🔀 **Skenario what-if** — "bagaimana jika faktor grid turun 30%?" → bandingkan baseline vs skenario.
- 📄 **Laporan** Excel (`.xlsx`) + cetak PDF, lengkap dengan **methodology appendix** (semua faktor + sumber).
- 📡 **IoT ingestion** (`/ingest`, `/ingest/batch`) — data sensor masuk sebagai aktivitas, auth API key terpisah.
- 🌐 **Dua mode**: backend penuh (riset, multi-user, tersimpan) **dan** demo statis browser (angka identik).

---

## 🏗️ Arsitektur

```
┌──────────────────────────────────────────────────────────────┐
│                       DOMAIN MODULES                          │
│   Personal │ Organizational │ Sector (Tani/Energi) │ Product  │
│   (tiap domain: input schema · kategori · strategy · agregasi)│
└───────────────────────────┬──────────────────────────────────┘
                            │ kontrak DomainModule
┌───────────────────────────▼──────────────────────────────────┐
│                           CORE                                │
│  Factor Registry · Calculation Engine · GWP · Units           │
│  Uncertainty (analitis + Monte Carlo) · Provenance (immutable)│
└───────────────────────────┬──────────────────────────────────┘
        ┌───────────────────┼───────────────────┐
    REST API           IoT Ingestion        Laporan (Excel/PDF)
   (CRUD + run)       (sensor → aktivitas)   (+ methodology appendix)
```

Form di frontend **dirender dinamis dari JSON Schema** tiap domain — menambah field tidak
perlu mengubah kode form.

---

## 🧰 Tech stack

| Layer | Pilihan |
|---|---|
| Backend | **FastAPI** (async) · SQLAlchemy 2.x · Alembic · Pydantic v2 |
| Database | **SQLite** (dev) — *Postgres-ready* (UUID + `JSON().with_variant(JSONB)`; ganti `DATABASE_URL`) |
| Frontend | **React + TypeScript + Vite** (design system "scientific instrument", lihat `DESIGN.md`) |
| Uncertainty | NumPy (Monte Carlo) |
| Laporan | openpyxl (Excel) · cetak HTML browser (PDF) |
| Auth | JWT (user) · API key terpisah (ingestion mesin) |

---

## ⚡ Menjalankan

### Opsi A — Demo (paling cepat)
Cukup buka **[demo live](https://nothinx.github.io/web-based-emisi-carbon/)**. Selesai.

### Opsi B — Lokal, versi backend penuh

<details open>
<summary><b>Backend</b> (API di <code>http://localhost:8000</code>, dok: <code>/docs</code>)</summary>

```bash
cd backend
uv venv --python 3.12
uv pip install -e ".[dev,report]"     # report = openpyxl (export Excel)

# buat tabel + seed faktor contoh
./.venv/Scripts/python -m app.cli seed

# jalankan API
./.venv/Scripts/python -m uvicorn app.main:app --reload
```
</details>

<details open>
<summary><b>Frontend</b> (UI di <code>http://localhost:5173</code>)</summary>

```bash
cd frontend
npm install
npm run dev      # proxy /api -> :8000
```
> Catatan: gunakan `http://localhost:5173` (Vite bind ke `localhost`, bukan `127.0.0.1`).
</details>

Migrasi (Postgres/produksi): `./.venv/Scripts/python -m alembic upgrade head`

---

## 🧪 Testing

```bash
cd backend && ./.venv/Scripts/python -m pytest      # 40 tests
```
Mencakup uji **reproducibility** (recompute dari snapshot = angka identik), immutability
snapshot terhadap perubahan versi faktor, konversi GWP & unit, rollup Scope 1/2/3, Monte
Carlo (seeded), strategy IPCC tier, dan ekspor laporan.

---

## 📁 Struktur proyek

```
backend/
  app/
    core/        # engine, strategies (Multiply + IPCC tier), gwp, units, uncertainty, provenance
    factors/     # registry + seed loader
    domains/     # personal · organizational · sector · product
    api/          # factors, projects, domains, reports, ingest, auth
    models/ · schemas/
  tests/         # uji reproducibility & per fase
frontend/
  src/
    pages/       # kalkulator tiap domain + Factor Registry
    components/  # charts, laporan, app shell
    lib/         # staticEngine.ts / staticBackend.ts (port engine ke browser)
docs/
  methodology.md # sumber faktor, asumsi, batasan — dijaga seiring jalan
```

---

## 📐 Metodologi & kejujuran ilmiah

Semua metode, faktor, asumsi, dan **batasan** didokumentasikan di
**[`docs/methodology.md`](docs/methodology.md)**.

> ⚠️ **Penting:** sebagian faktor masih **PLACEHOLDER** (mis. grid PLN, beberapa default
> IPCC, faktor material LCA proxy) — nilai indikatif yang **wajib diganti dengan faktor
> resmi/terbaru sebelum dipakai untuk publikasi**. Faktor yang ditandai placeholder tampil
> dengan peringatan di hasil & appendix. Ini disengaja: alat menyediakan kerangka yang
> benar, sourcing faktor adalah pekerjaan berkelanjutan tersendiri.

---

## 🗺️ Status & roadmap

| Fase | Cakupan | Status |
|---|---|:--:|
| 0 | Core: data model, engine, factor registry, provenance | ✅ |
| 1 | Personal | ✅ |
| 2 | Organizational (Scope 1/2/3) + pelaporan Excel/PDF | ✅ |
| 3 | Uncertainty (Monte Carlo) + sensitivity + scenario | ✅ |
| 4 | Sector (IPCC tier) + IoT ingestion | ✅ |
| 5 | Product/LCA parametrik | ✅ |

**Lanjutan:** faktor emisi lokal Indonesia menggantikan placeholder · Scope 3 lengkap (15
kategori) · LULUCF · IPCC Tier 2/3 · integrasi database LCA non-proxy · UI manajemen skenario.

---

## 🙏 Sumber data (contoh seed)

IPCC (AR6 GWP, 2019 Refinement AFOLU) · UK DEFRA/BEIS · Poore & Nemecek (2018) · IEA ·
PLN/KLHK (grid Indonesia, placeholder). Sitasi lengkap ada di setiap faktor & di
`docs/methodology.md`.

---

## 📜 Lisensi

Lisensi belum ditetapkan — hak cipta penulis. Hubungi pemilik repo untuk penggunaan/kontribusi.

<div align="center">
<sub>Dibangun dengan fokus pada kebenaran metodologi: reproducible, traceable, uncertainty-aware.</sub>
</div>
