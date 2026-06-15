# Design

> Seed design system untuk frontend React. Tema: **scientific instrument** —
> presisi, tenang, data-dense, light. Pure-white surface; amber sebagai warna
> brand/aksi; ink-blue dingin sebagai warna struktural data. Strategi warna:
> **restrained** (netral + dua warna brand yang dipakai disiplin). Re-run
> `/impeccable document` setelah token CSS nyata ada untuk menangkap sistem aktual.

## Theme

Light. Skena fisik: peneliti/analis di meja kerja kantor/lab di siang hari,
sesi panjang membaca tabel angka & teks metodologi. Light theme menurunkan
kelelahan untuk kerja dokumen-berat dan selaras dengan output cetak/PDF.

## Color

OKLCH di seluruh sistem. Amber (hue ~75°) adalah suara brand; ink-blue dingin
(hue ~245°) memberi struktur untuk data. Surface tetap putih murni — kehangatan
tidak diletakkan di background.

### Neutrals & surfaces
| Token | OKLCH | Peran |
|---|---|---|
| `--bg` | `oklch(1 0 0)` | latar aplikasi (putih murni) |
| `--surface` | `oklch(0.985 0.002 255)` | panel, kartu, dialog |
| `--surface-2` | `oklch(0.965 0.003 255)` | header tabel, inset, kode |
| `--border` | `oklch(0.912 0.004 255)` | garis pemisah 1px |
| `--border-strong` | `oklch(0.84 0.006 255)` | border input fokus, divider tegas |

### Text (ink ramp)
| Token | OKLCH | Kontras vs putih | Peran |
|---|---|---|---|
| `--ink` | `oklch(0.24 0.012 255)` | ~14:1 | teks utama, angka |
| `--ink-2` | `oklch(0.40 0.014 255)` | ~7:1 | label, teks sekunder |
| `--muted` | `oklch(0.48 0.015 255)` | ~5:1 | teks tersier, hint, placeholder |

Catatan: `--muted` adalah lantai untuk teks; jangan pakai gray lebih terang
sebagai body. Placeholder memakai `--muted`, bukan abu pucat default.

### Brand & accent
| Token | OKLCH | Peran |
|---|---|---|
| `--primary` | `oklch(0.70 0.146 75)` | fill aksi utama (amber). Teks DI ATASNYA = `--ink` gelap, bukan putih |
| `--primary-strong` | `oklch(0.52 0.12 70)` | amber gelap untuk teks/ikon di atas putih (≥4.5:1) |
| `--accent` | `oklch(0.50 0.11 245)` | link, seri data utama, fokus ring (ink-blue) |
| `--accent-soft` | `oklch(0.95 0.02 245)` | latar highlight lembut, baris terpilih |

### Semantic
| Token | OKLCH | Peran |
|---|---|---|
| `--success` | `oklch(0.55 0.11 150)` | status valid/aktif |
| `--warning` | `oklch(0.66 0.14 75)` | placeholder/credibility tier rendah, asumsi |
| `--danger` | `oklch(0.55 0.18 27)` | error, faktor kedaluwarsa |

### Data-viz categorical (scope / gas / kategori)
Dipakai untuk seri chart & badge. Selalu **dipasangkan label/pola**, tidak
mengandalkan warna saja (a11y color-blind).
`amber 0.70/0.146/75` · `ink-blue 0.55/0.12/245` · `teal 0.60/0.10/195` ·
`violet 0.55/0.12/300` · `clay 0.58/0.13/35` · `slate 0.55/0.03/255`
Uncertainty/CI band: isian `--accent` pada alpha 0.15–0.22.

## Typography

Tiga family pada sumbu kontras jelas (serif / sans / mono):
- **Heading — Source Serif 4** (scholarly serif): judul halaman, judul section,
  judul laporan. `text-wrap: balance` pada h1–h3.
- **UI/Body — Inter**: navigasi, label, form, prosa. Body line-length 65–75ch.
- **Data/Mono — IBM Plex Mono**: angka emisi, unit, faktor ID, versi, snapshot,
  kode. Setiap nilai numerik & unit dirender mono untuk alignment kolom.

Display heading ceiling: `clamp()` max ≤ 3rem (alat, bukan landing — tidak
berteriak). Letter-spacing display ≥ -0.02em.

## Spacing & Radius

- Spacing base 4px: `4 8 12 16 24 32 48 64`.
- Radius kecil, instrumen: `--r-sm 4px`, `--r-md 6px`, `--r-lg 10px`. Tidak ada
  pill kecuali badge status.
- Density: tabel kompak (row height ~36px), tapi padding sel cukup untuk scan.

## Components (arah)

- **Tabel data** adalah komponen utama (faktor, aktivitas, hasil). Sticky header,
  kolom angka rata-kanan & mono, baris hover halus, zebra opsional via `--surface-2`.
- **Provenance viewer**: panel/disclosure yang membekukan & menampilkan
  `factor_snapshot` (sumber, URL, versi, GWP set, asumsi).
- **CI band / uncertainty**: chart dengan area band + garis mean; tooltip
  menampilkan mean & 95% CI dalam mono.
- **Versi faktor**: timeline/disclosure menampilkan `valid_from`–`valid_to`,
  badge `is_active`.
- Hindari grid kartu seragam, hero-metric, eyebrow uppercase per-section,
  side-stripe border, gradient text, glassmorphism.

## Motion

Intentional & halus. Ease-out-expo untuk transisi panel/disclosure (150–220ms).
Stagger ringan saat baris tabel/hasil pertama kali masuk. Tidak ada bounce.
Wajib ada fallback `@media (prefers-reduced-motion: reduce)` (crossfade/instant).
Reveal hanya memperkuat konten yang sudah terlihat — jangan gate visibility.
