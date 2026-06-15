# Carbon Emission Engine

Web app perhitungan emisi karbon (CO₂e) tingkat penelitian — **reproducible,
traceable, uncertainty-aware**, dengan prioritas faktor emisi lokal Indonesia.
Satu *core engine* + *domain modules* (Personal, Organizational, Sector, Product/LCA).

Status: **Phase 0 — Core scaffolding** selesai (lihat `docs/methodology.md` & prompt).

## Arsitektur

- `backend/` — FastAPI + SQLAlchemy 2.x (async) + Alembic. SQLite untuk dev,
  **Postgres-ready** (tipe UUID & JSON→JSONB variant; ganti `DATABASE_URL` saja).
- `frontend/` — React + TypeScript + Vite. Factor Registry CRUD UI ("scientific
  instrument" design system, lihat `DESIGN.md`).
- `docs/methodology.md` — sumber faktor, asumsi, batasan.

## Menjalankan

### Backend
```bash
cd backend
uv venv --python 3.12
uv pip install -e ".[dev]"
# (opsional) salin .env.example -> .env

# buat tabel + seed faktor contoh
./.venv/Scripts/python -m app.cli seed

# jalankan API (http://localhost:8000, dok: /docs)
./.venv/Scripts/python -m uvicorn app.main:app --reload
```

Migrasi (Postgres/produksi):
```bash
./.venv/Scripts/python -m alembic upgrade head
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173 (proxy /api -> :8000)
```

Catatan: Vite mengikat ke `localhost`; gunakan `http://localhost:5173`.

## Test
```bash
cd backend && ./.venv/Scripts/python -m pytest
```
Mencakup uji **reproducibility** (recompute dari snapshot = angka identik),
immutability snapshot terhadap perubahan versi faktor, konversi GWP per-gas,
konversi unit, dan rentang ketidakpastian.

## Prinsip non-negotiable
Lihat `prompt-build-carbon-calculator.md` §2 dan `PRODUCT.md`. Singkatnya: hasil
immutable, faktor versioned (tak pernah ditimpa), snapshot beku (bukan referensi
live), faktor = data + sitasi (tak di-hardcode), angka selalu berkonteks ketidakpastian.
