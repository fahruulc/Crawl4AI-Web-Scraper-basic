# PRD: Config-Driven Web Scraper (Crawl4AI + Python)

Versi: 0.1 (draf) · Tanggal: 9 Nov 2026
Atribusi: proyek ini memakai Crawl4AI (https://github.com/unclecode/crawl4ai) untuk web data extraction. Baris ini wajib dicantumkan di README dan deskripsi video (syarat atribusi di README Crawl4AI).

## 1. Ringkasan

Scraper berbasis Python yang **tidak terikat ke satu website**. URL, mode ekstraksi, dan skema data didefinisikan di file konfigurasi per target. Mengganti target = menambah atau mengubah satu file config, tanpa menyentuh kode inti.

## 2. Tujuan dan non-tujuan

**Tujuan**
- Mengambil data terstruktur (contoh studi kasus: nama, harga, stok produk supplier) dari beberapa website berlayout berbeda.
- Berjalan di laptop spesifikasi rendah (Intel Core i5 gen 6) tanpa GPU dan tanpa biaya wajib.
- Hasil tersimpan rapi, bisa dijalankan ulang tanpa data ganda.

**Non-tujuan (versi 0.1)**
- Tidak membypass CAPTCHA, login berbayar, atau proteksi anti-bot.
- Tidak mengambil data pribadi.
- Tidak menjalankan LLM lokal (Ollama) sebagai default.
- Tidak ada UI web; cukup CLI.

## 3. Pengguna dan skenario

Staf pengadaan gudang (atau kreator yang mendemokannya) ingin menyatukan katalog beberapa supplier ke satu tabel. Skenario utama:
1. Tambah target baru: salin `targets/_template.yaml`, isi URL dan skema, jalankan.
2. Layout situs berubah: regenerasi schema atau ganti mode ke `llm`, lalu jalankan ulang.
3. Jalankan rutin dan lihat perubahan harga atau stok.

## 4. Konsep: satu mesin, banyak target

```
targets/*.yaml  ->  runner  ->  Crawl4AI (browser) -> extractor (css | llm)
                                                      -> validator (Pydantic)
                                                      -> storage (SQLite)
```

Contoh `targets/supplier_a.yaml`:

```yaml
name: supplier_a
start_urls:
  - "https://contoh-situs-latihan.example/katalog"
mode: css            # css | llm
schema_file: schemas/supplier_a.json    # dipakai jika mode=css
llm:                                    # dipakai jika mode=llm
  provider: "gemini/<nama-model>"       # cek nama model terbaru di AI Studio
  instruction: "Ekstrak nama produk, harga, dan stok."
rate_limit_seconds: 3
scroll_full_page: true
max_pages: 20
```

**Batasan penting:** mode `css` gratis dan cepat, tetapi selector-nya spesifik per situs. Mode `llm` lebih tahan perubahan layout dan bisa dipakai lintas situs dengan skema Pydantic yang sama, tetapi memakai kuota API. Strategi hemat: gunakan `generate_schema` sekali untuk menulis schema CSS, lalu jalankan rutin tanpa LLM.

## 5. Kebutuhan fungsional

| ID | Kebutuhan | Prioritas |
|----|-----------|-----------|
| F1 | Baca semua file `targets/*.yaml`, jalankan satu per satu atau pilih lewat CLI (`--target supplier_a`) | Wajib |
| F2 | Mode `css`: ekstraksi dengan `JsonCssExtractionStrategy` dari schema file | Wajib |
| F3 | Mode `llm`: ekstraksi dengan `LLMExtractionStrategy` + model Pydantic | Wajib |
| F4 | Dukung halaman dinamis (tunggu elemen, scroll penuh) | Wajib |
| F5 | Validasi tiap record dengan Pydantic; record tidak valid dicatat, bukan disimpan | Wajib |
| F6 | Simpan ke SQLite dengan kunci unik (idempotent), catat waktu ambil data | Wajib |
| F7 | Deteksi perubahan (harga/stok berbeda dari data sebelumnya) | Sebaiknya |
| F8 | Ekspor ke CSV | Sebaiknya |
| F9 | Cache hasil fetch untuk menghindari request ulang saat development | Sebaiknya |

## 5a. Kebutuhan non-fungsional

- **Resource rendah:** satu halaman pada satu waktu secara default; naikkan konkurensi hanya setelah benchmark di laptop target.
- **Reprodusibel:** versi Python dan semua dependency di-pin (`requirements.txt` dengan versi tetap, mis. `crawl4ai==0.9.5`).
- **Ketahanan:** retry dengan jeda bertambah untuk error sementara; timeout jelas; satu target gagal tidak menghentikan target lain.
- **Observability:** log ke file (target, URL, jumlah record, error, durasi).

## 6. Best practice pengembangan

**Etika dan legal** (bukan nasihat hukum; periksa aturan tiap situs)
- Baca `robots.txt` dan Terms of Service sebelum menambah target; simpan catatannya di config.
- Beri jeda antar request (`rate_limit_seconds`) dan batasi `max_pages`.
- Jangan scrape data pribadi; di Indonesia perhatikan aturan pelindungan data pribadi.
- Untuk demo dan latihan, pakai situs yang memang disediakan untuk latihan scraping.

**Kualitas kode**
- Pisahkan: config, fetcher, extractor, validator, storage. Satu tanggung jawab per modul.
- Skema data dideklarasikan sekali (Pydantic) dan dipakai oleh mode `css` maupun `llm`.
- Simpan sampel HTML di `tests/fixtures/` dan uji extractor terhadap HTML itu (Crawl4AI mendukung input `raw:`), jadi tes tidak perlu internet.
- Jangan hardcode URL, selector, atau API key di kode.

**Keamanan dan dependency**
- Gunakan virtual environment; pin versi; baca release notes sebelum upgrade (Crawl4AI pernah merilis hotfix karena insiden supply chain pada dependency).
- API key di `.env`, masukkan ke `.gitignore`; jangan tampil di layar saat rekam video.
- Periksa paket apa yang dipasang bila agent AI menjalankan `pip install`.
- Bila memakai Docker server Crawl4AI, wajib set `CRAWL4AI_API_TOKEN` dan pin versi image.

**Penggunaan LLM**
- Tier gratis memiliki batas yang berubah-ubah dan syarat penggunaan data; cek di dashboard akun sebelum merancang volume.
- Cache hasil LLM per URL+hash konten agar tidak memanggil ulang.
- Sediakan fallback: bila kuota habis, lewati record dan catat, jangan crash.

## 7. Struktur proyek

```
scraper/
  targets/            # satu YAML per situs
  schemas/            # schema CSS dan model Pydantic
  src/
    config.py  runner.py  extract_css.py  extract_llm.py
    validate.py  storage.py  report.py
  tests/fixtures/     # sampel HTML
  data/               # SQLite dan CSV (di-.gitignore)
  .env.example  requirements.txt  README.md  PRD.md
```

## 8. Model data (contoh)

Tabel `products`: `id`, `target`, `source_url`, `name`, `price`, `stock`, `scraped_at`.
Kunci unik: (`target`, `source_url`, `name`). Riwayat harga disimpan di tabel terpisah `price_history`.

## 9. Biaya dan batas gratis

| Komponen | Status | Catatan |
|----------|--------|---------|
| Python, Crawl4AI, Playwright/Chromium | Gratis | Open source; Crawl4AI berlisensi Apache-2.0 dengan syarat atribusi |
| SQLite, Pydantic, YAML | Gratis | |
| Mode `css` | Gratis penuh | Tanpa API key |
| Mode `llm` via API gratis | Gratis dengan batas | Batas berubah; verifikasi sebelum implementasi |
| LLM lokal (Ollama) | Gratis, tetapi lambat | Tidak disarankan di CPU gen 6 tanpa GPU (perkiraan) |

## 10. Kriteria penerimaan

- Menambah target baru hanya dengan menambah file YAML (dan schema bila mode `css`), tanpa mengubah kode `src/`.
- Dua target dengan layout berbeda menghasilkan tabel dengan skema yang sama.
- Menjalankan dua kali berturut-turut tidak menggandakan data.
- Satu target yang gagal tidak menghentikan target lain.
- Seluruh tes lulus offline memakai HTML fixture.
- Benchmark di laptop target tercatat (waktu, RAM, jumlah request LLM).

## 11. Milestone

1. **M1 Fondasi:** setup, satu target mode `css`, simpan ke SQLite.
2. **M2 Multi-target:** loader config, target kedua berlayout beda.
3. **M3 LLM:** mode `llm` + validasi Pydantic + cache.
4. **M4 Produksi ringan:** retry, log, deteksi perubahan, ekspor CSV.
5. **M5 Dokumentasi:** README, atribusi, benchmark.

## 12. Risiko

| Risiko | Mitigasi |
|--------|----------|
| Layout situs berubah, selector patah | Mode `llm` atau regenerasi schema; tes fixture |
| Kuota LLM gratis habis atau berubah | Cache, fallback ke `css`, verifikasi batas sebelum rekam |
| API Crawl4AI berubah antar versi | Pin versi; rujuk dokumentasi resmi |
| Situs melarang scraping | Cek ToS dan robots.txt; pilih target legal |
| RAM laptop terbatas | Konkurensi 1, tutup tab/proses lain, ukur saat benchmark |

## 13. Pertanyaan terbuka

- Berapa RAM dan OS mesin pengembangan?
- Penyimpanan akhir: tetap SQLite, atau pindah ke PostgreSQL (mis. Supabase) untuk video lanjutan?
- Model LLM dan penyedia mana yang dipakai setelah batas free tier diverifikasi?
