# Config-Driven Web Scraper (Crawl4AI + Python)

> **Atribusi:** Proyek ini memakai [Crawl4AI](https://github.com/unclecode/crawl4ai) untuk web data extraction. Baris ini wajib dicantumkan di README dan deskripsi video (syarat atribusi di README Crawl4AI).

Scraper berbasis Python yang **tidak terikat ke satu website**. URL, mode ekstraksi, dan skema data didefinisikan di file konfigurasi per target di direktori `targets/`. Mengganti atau menambah target baru = cukup menambah satu file YAML di `targets/` dan satu schema di `schemas/`, tanpa menyentuh kode di `src/`.

---

## 🛠️ Persyaratan Lingkungan
- Python 3.10+ (diuji pada Python 3.12)
- Virtual Environment aktif (`.venv`)

---

## 📦 Instalasi & Aktivasi Virtual Environment

### 1. Buat Virtual Environment
```bash
python -m venv .venv
```

### 2. Aktifkan Virtual Environment sesuai OS & Shell Anda

- **PowerShell (Windows):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
  *(Jika muncul error execution policy, jalankan: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned`)*

- **Git Bash (Windows):**
  ```bash
  source .venv/Scripts/activate
  ```

- **Linux / macOS:**
  ```bash
  source .venv/bin/activate
  ```

### 3. Pasang Dependensi & Browser Playwright
```bash
pip install -r requirements.txt
python -m playwright install chromium
```

---

## 🚀 Menjalankan Scraper (Running)

Scraper dijalankan melalui modul `src.runner`. Anda dapat menjalankan scraper secara dinamis dengan mengganti parameter placeholder `[nama_target]`, `[path/ke/fixture.html]`, atau `[path/ke/database.db]`.

### Parameter CLI Tersedia
- `--target` atau `-t` : Nama target konfigurasi tanpa ekstensi `.yaml` (misal: `ecommerce_demo`, `books_toscrape`, `job`).
- `--db` : Path ke file SQLite database (default: `data/scraper.db`).
- `--fixture` atau `-f` : Path file HTML lokal untuk testing offline tanpa koneksi internet.
- `--targets-dir` : Direktori kumpulan file YAML target (default: `targets`).

---

### 1. Menjalankan Target Spesifik (Live Internet)
Ganti `[nama_target]` dengan target yang diinginkan (contoh: `ecommerce_demo`, `books_toscrape`, atau `job`).

- **PowerShell:**
  ```powershell
  python -m src.runner --target [nama_target]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo
  ```

- **Git Bash:**
  ```bash
  python -m src.runner --target [nama_target]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo
  ```

- **Linux / macOS:**
  ```bash
  python3 -m src.runner --target [nama_target]
  # Contoh konkret:
  python3 -m src.runner --target ecommerce_demo
  ```

---

### 2. Menjalankan dengan Database Kustom
Secara default, data disimpan ke `data/scraper.db`. Jika ingin menggunakan database kustom `[path/ke/database.db]`:

- **PowerShell:**
  ```powershell
  python -m src.runner --target [nama_target] --db [path/ke/database.db]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo --db data/custom_test.db
  ```

- **Git Bash / Linux:**
  ```bash
  python -m src.runner --target [nama_target] --db [path/ke/database.db]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo --db data/custom_test.db
  ```

---

### 3. Menjalankan Target Mode Offline (HTML Fixture)
Gunakan opsi `--fixture` untuk mengekstrak file HTML lokal (cocok untuk pengujian atau saat internet lambat):

- **PowerShell:**
  ```powershell
  python -m src.runner --target [nama_target] --fixture [path/ke/fixture.html]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo --fixture tests/fixtures/ecommerce_demo.html
  ```

- **Git Bash / Linux:**
  ```bash
  python -m src.runner --target [nama_target] --fixture [path/ke/fixture.html]
  # Contoh konkret:
  python -m src.runner --target ecommerce_demo --fixture tests/fixtures/ecommerce_demo.html
  ```

---

### 4. Menjalankan Seluruh Target Sekaligus
Jika argumen `--target` ditiadakan, scraper akan menjalankan seluruh file YAML yang ada di folder `targets/`:

- **PowerShell / Git Bash:**
  ```bash
  python -m src.runner
  ```

- **Linux / macOS:**
  ```bash
  python3 -m src.runner
  ```

---

## 📊 Menampilkan & Memeriksa Data di Database (Show Data)

Scraper ini mendukung **penyimpanan fleksibel & dinamis** ke SQLite:
1. **Target Produk/Katalog (misal `books_toscrape`, `ecommerce_demo`)**: Otomatis disimpan ke tabel **`products`** (kolom: `id`, `target`, `source_url`, `name`, `price`, `stock`, `scraped_at`) dan dicatat riwayatnya di **`price_history`**.
2. **Target Kustom/Non-Produk (misal `job`)**: Otomatis membuat tabel terpisah sesuai nama target (misal tabel **`job`**) dengan kolom dinamis mengikuti field schema Anda (misal: `id`, `target`, `source_url`, `scraped_at`, `job_name`, `company`, `location`).

Berikut perintah dinamis untuk melihat isi database langsung dari terminal:

### 1. Melihat Daftar Tabel yang Ada di Database
Ganti `[path/ke/db.db]` sesuai lokasi database:

- **PowerShell:**
  ```powershell
  python -c "import sqlite3; conn = sqlite3.connect('[path/ke/db.db]'); print('Daftar Tabel:', [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'\").fetchall()])"
  
  # Contoh pada data/job.db:
  python -c "import sqlite3; conn = sqlite3.connect('data/job.db'); print('Daftar Tabel:', [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'\").fetchall()])"
  ```

- **Git Bash & Linux / macOS:**
  ```bash
  python -c 'import sqlite3; conn = sqlite3.connect("[path/ke/db.db]"); print("Daftar Tabel:", [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type=\"table\" AND name NOT LIKE \"sqlite_%\"").fetchall()])'
  ```

---

### 2. Menampilkan Data Tabel Dinamis (Contoh: Tabel `job`)
Ganti `[nama_tabel]` dan `[path/ke/db.db]` sesuai target:

- **PowerShell:**
  ```powershell
  python -c "import sqlite3, json; conn = sqlite3.connect('[path/ke/db.db]'); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute('SELECT * FROM [nama_tabel] LIMIT 10')]; print(json.dumps(rows, indent=2))"
  
  # Contoh konkret untuk tabel job di data/job.db:
  python -c "import sqlite3, json; conn = sqlite3.connect('data/job.db'); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute('SELECT id, job_name, company, location FROM job LIMIT 5')]; print(json.dumps(rows, indent=2))"
  ```

- **Git Bash & Linux / macOS:**
  ```bash
  python -c 'import sqlite3, json; conn = sqlite3.connect("[path/ke/db.db]"); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute("SELECT * FROM [nama_tabel] LIMIT 10")]; print(json.dumps(rows, indent=2))'
  
  # Contoh konkret untuk tabel job di data/job.db:
  python -c 'import sqlite3, json; conn = sqlite3.connect("data/job.db"); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute("SELECT id, job_name, company, location FROM job LIMIT 5")]; print(json.dumps(rows, indent=2))'
  ```

---

### 3. Menampilkan Data Tabel Standar `products`
Untuk target yang memiliki `name` dan `price`:

- **PowerShell:**
  ```powershell
  python -c "import sqlite3, json; conn = sqlite3.connect('data/scraper.db'); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute('SELECT target, name, price, stock FROM products WHERE target = ? LIMIT 10', ('[nama_target]',))]; print(json.dumps(rows, indent=2))"
  
  # Contoh konkret:
  python -c "import sqlite3, json; conn = sqlite3.connect('data/scraper.db'); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute('SELECT target, name, price, stock FROM products WHERE target = ? LIMIT 10', ('ecommerce_demo',))]; print(json.dumps(rows, indent=2))"
  ```

- **Git Bash & Linux / macOS:**
  ```bash
  python -c 'import sqlite3, json; conn = sqlite3.connect("data/scraper.db"); conn.row_factory = sqlite3.Row; rows = [dict(r) for r in conn.execute("SELECT target, name, price, stock FROM products WHERE target = ? LIMIT 10", ("[nama_target]",))]; print(json.dumps(rows, indent=2))'
  ```

---

### 4. Menampilkan Ringkasan Jumlah Baris
Melihat total data per target:

- **PowerShell:**
  ```powershell
  python -c "import sqlite3; conn = sqlite3.connect('data/job.db'); print('Total baris:', conn.execute('SELECT COUNT(*) FROM job').fetchone()[0])"
  ```

- **Git Bash & Linux / macOS:**
  ```bash
  python -c 'import sqlite3; conn = sqlite3.connect("data/job.db"); print("Total baris:", conn.execute("SELECT COUNT(*) FROM job").fetchone()[0])'
  ```

---

### 5. Menggunakan SQLite CLI (`sqlite3`)

Jika pada sistem Anda sudah terpasang program `sqlite3`:

- **PowerShell / Git Bash / Linux:**
  ```bash
  sqlite3 -header -column data/job.db "SELECT id, job_name, company, location FROM job LIMIT 10;"
  ```

---

## 🧪 Menjalankan Tes Otomatis (Offline)

Rangkaian pengujian berjalan 100% offline tanpa membutuhkan koneksi internet, memanfaatkan HTML fixtures:

- **PowerShell:**
  ```powershell
  pytest -v
  ```

- **Git Bash & Linux / macOS:**
  ```bash
  pytest -v
  ```
