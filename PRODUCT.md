# Product

## Register

product

## Users

Peneliti, analis keberlanjutan, dan praktisi GHG accounting di Indonesia
(kampus, lembaga riset, konsultan lingkungan, tim ESG korporat). Mereka bekerja
di meja kerja/lab dalam sesi panjang: memasukkan data aktivitas, memilih faktor
emisi, menjalankan perhitungan, lalu membaca tabel angka, rentang ketidakpastian,
dan laporan metodologi. Kebutuhan utama mereka bukan "angka cepat" melainkan
**angka yang bisa dipertanggungjawabkan secara akademik**: dapat dihitung ulang,
ditelusuri sumbernya, dan dilaporkan dengan ketidakpastian.

## Product Purpose

Web app perhitungan emisi karbon (CO₂e) tingkat penelitian untuk 4 domain
(Personal, Organizational/GHG Protocol, Product/LCA, Sector tani-energi) di atas
satu core engine. Pembeda dari kalkulator awam: **reproducibility** (snapshot
faktor beku per hasil), **traceability** (setiap angka tertaut ke faktor, versi,
sumber, GWP set, asumsi), **uncertainty-awareness** (rentang, bukan angka tunggal
palsu-presisi), dan **faktor emisi lokal Indonesia** sebagai prioritas.
Sukses = seorang peneliti bisa menjalankan ulang sebuah perhitungan berbulan-bulan
kemudian dan mendapatkan angka identik, lengkap dengan appendix metodologi yang
dapat dipertahankan dalam publikasi.

## Brand Personality

Presisi, tenang, kredibel — sebuah **instrumen ilmiah**, bukan produk marketing.
Voice: lugas, teknis, jujur tentang batasan (limitation dinyatakan, bukan
disembunyikan). Antarmuka menimbulkan rasa **percaya** dan **kontrol**: data
padat tapi terbaca, angka dan unit selalu eksplisit, provenance selalu satu klik.
Tiga kata: *teliti, transparan, tepercaya.*

## Anti-references

- Kalkulator karbon konsumen yang ceria (badge, emoji daun, gamifikasi, "you saved
  X trees!") — kita serius dan netral.
- Dashboard SaaS generik: grid kartu metrik seragam, hero-metric raksasa dengan
  gradient, eyebrow uppercase di tiap section.
- Greenwashing aesthetic: hijau jenuh di mana-mana, gradient hijau-biru, stok foto
  panel surya. Warna adalah alat baca data, bukan klaim moral.
- Angka tunggal tanpa konteks ketidakpastian atau sumber.

## Design Principles

1. **Angka harus jujur** — selalu tampilkan unit, dan ketidakpastian (CI band)
   menyertai setiap nilai emisi. Tidak ada presisi palsu.
2. **Provenance selalu dekat** — sumber faktor, versi, GWP set, dan asumsi bisa
   ditelusuri dari hasil mana pun tanpa berpindah konteks.
3. **Density yang terbaca** — ini alat data-dense; utamakan tabel & angka yang
   rapi dan scannable di atas dekorasi. Whitespace untuk ritme, bukan kekosongan.
4. **Imutabilitas terlihat** — UI menegaskan bahwa hasil beku & faktor berversi;
   "edit" berarti versi baru, bukan menimpa.
5. **Nyatakan batasan** — penyederhanaan (mis. LCA parametrik v1) ditampilkan
   sebagai limitation eksplisit, bukan disembunyikan.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Body text ≥4.5:1, teks besar ≥3:1. Data viz tidak boleh
mengandalkan warna saja — pasangkan dengan pola/label/bentuk (penting untuk
color-blind, mengingat banyak data per-scope/per-gas). Dukung `prefers-reduced-motion`.
Antarmuka bilingual-aware: UI Bahasa Indonesia, istilah teknis (Scope, GWP, CO₂e,
LCA) dibiarkan dalam bahasa Inggris sesuai konvensi bidang.
