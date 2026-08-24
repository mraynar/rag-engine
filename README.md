# TPS RAG Engine

Proyek mesin pencari pintar berbasis **RAG (Retrieval-Augmented Generation)** menggunakan Next.js (frontend), FastAPI (backend), ChromaDB (vector store lokal), dan Gemini (embedding & text generation).

Sistem ini dirancang untuk mensinkronisasi dan mengindeks dokumen secara dinamis dari **SharePoint/OneDrive**, **Google Drive/Sheets**, serta file manual (PDF, Excel, Word, PPTX, TXT, dan Gambar) untuk memberikan jawaban berbasis konteks dokumen organisasi.

---

> [!IMPORTANT]  
> **Panduan Cepat Pengujian:**
> 1. Jalankan aplikasi menggunakan **Docker Compose** (rekomendasi) atau **Manual Setup**.
> 2. Buka tab **Konfigurasi** di UI web ([http://localhost:3000](http://localhost:3000)).
> 3. Masukkan **Gemini API Key** Anda di kolom kandidat utama, lalu klik **Simpan** dan **Aktifkan**.
> 4. Untuk pengujian cepat, masuk ke menu **Kelola Sumber Data** di dropdown kanan atas, pilih tab **Dokumen Manual**, dan unggah berkas contoh bawaan di: `data/documents/OVERVIEW VESSEL.xlsx`.
> 5. Lakukan sinkronisasi (jika cloud) atau pastikan berkas manual aktif, lalu beralih ke halaman **Chat** untuk mulai bertanya.

---

## Persyaratan Sistem & Instalasi

Pilih salah satu dari dua cara untuk menjalankan aplikasi ini:

### Cara 1: Menggunakan Docker (Rekomendasi & Instan)

Pastikan Anda memiliki **Docker** & **Docker Desktop** terpasang di komputer Anda.

1. **Masuk ke Folder Project**
   ```bash
   cd rag-engine
   ```

2. **Jalankan Aplikasi**
   ```bash
   docker compose down && docker compose up --build
   ```
   *Perintah ini otomatis mengunduh dependencies, membangun container backend (FastAPI, port `8000`) dan frontend (Next.js, port `3000`), lalu menjalankannya secara paralel.*

3. **Akses Layanan**
   - **Frontend Web UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Healthcheck & Status API:** [http://localhost:8000/health](http://localhost:8000/health)

---

### Cara 2: Manual Setup (Tanpa Docker)

Jika Anda ingin menjalankan atau memprogram ulang service di luar container:

#### A. BACKEND (FastAPI)
1. Masuk ke folder root `rag-engine/` dan buat virtual environment Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Untuk Windows: venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. (Opsional) Jalankan Unit & Integration Test Suite:
   ```bash
   python3 -m unittest discover tests
   ```
4. Jalankan server FastAPI dengan Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### B. FRONTEND (Next.js)
1. Buka terminal baru dan masuk ke folder `frontend/`:
   ```bash
   cd frontend
   ```
2. Install NodeJS dependencies:
   ```bash
   npm install
   ```
3. Jalankan server development Next.js:
   ```bash
   npm run dev
   ```
   Aplikasi frontend akan berjalan di [http://localhost:3000](http://localhost:3000).

---

## Supabase Database & Auth Setup

Proyek ini terintegrasi dengan **Supabase Auth** untuk autentikasi user dan **Supabase Database (PostgreSQL)** untuk penyimpanan history chat yang aman.

### 1. Inisialisasi Environment Variables
Salin file template environment ke `.env` lokal:
* **Backend (`rag-engine/`):**
  ```bash
  cp .env.example .env
  ```
  *Buka `.env` dan masukkan `DATABASE_URL` (pooler), `DIRECT_URL` (direct connection), `SUPABASE_URL`, dan `SUPABASE_ANON_KEY` proyek Supabase Anda.*
* **Frontend (`rag-engine/frontend/`):**
  ```bash
  cp frontend/.env.local.example frontend/.env.local
  ```
  *Buka `frontend/.env.local` dan masukkan `NEXT_PUBLIC_SUPABASE_URL` serta `NEXT_PUBLIC_SUPABASE_ANON_KEY`.*

### 2. Jalankan Migrasi Database
Untuk membuat tabel `profiles`, `conversations`, dan `messages` beserta relasi, index, RLS (Row Level Security), policy keamanan, dan trigger otomatis, jalankan script migrasi di direktori root:
```bash
python scripts/migrate_supabase.py
```
*Script ini akan memindai folder `supabase/migrations/` dan mengeksekusi migrasi SQL secara berurutan.*

### 3. Konfigurasi Autentikasi di Supabase Dashboard
Pastikan Anda mengaktifkan **Email Auth Provider** di tab *Authentication -> Providers* pada dashboard Supabase Anda.

---

## Langkah Konfigurasi Kredensial (Live UI)

Sistem ini menggunakan konfigurasi dinamis berbasis JSON (`data/config_store.json`). **Tidak memerlukan restart server** saat Anda memperbarui API Key.

Setelah web terbuka di browser, buka tab **"Konfigurasi"** di menu navigasi:

1. **Gemini API Key (Wajib)**
   - Cari baris **gemini_api_key**. Anda bisa mengedit kandidat yang ada atau menambahkan kandidat API key baru (didapatkan dari Google AI Studio).
   - Klik tombol **"Aktifkan"** pada kandidat API Key yang ingin Anda gunakan.
2. **Kredensial Azure / Microsoft Graph API (Opsional)**
   - Digunakan untuk sinkronisasi resmi OneDrive/SharePoint organisasi TPS.
   - Masukkan JSON credential format: `{"tenant_id": "...", "client_id": "...", "client_secret": "..."}`.
   - Jika belum diisi, sistem otomatis masuk ke **Fallback Mode** (menggunakan tautan public share dengan parameter `download=1`).

---

## Alur Sinkronisasi & Manajemen Data

1. Buka tombol dropdown **"Sumber Data"** di bagian kanan atas navbar.
2. Klik tombol **"Kelola Sumber Data"** untuk menampilkan modal konfigurasi.
3. Di dalam modal tersebut, terdapat 2 pilihan tipe data:
   - **OneDrive / SharePoint / Google Drive:**
     - Masukkan nama kategori baru dan tautan berbagi berkas Excel spreadsheet Anda.
     - Klik tombol **Sync** untuk memicu pengunduhan, parsing spreadsheet, pembuatan embedding, dan pengindeksan ke ChromaDB.
   - **Dokumen Manual:**
     - Unggah file manual Anda langsung (`.pdf`, `.docx`, `.txt`, `.xlsx`, `.pptx`, dan berkas gambar seperti `.png`, `.jpg` untuk OCR).
     - Anda dapat menonaktifkan/mengaktifkan berkas secara dinamis dengan mengklik tombol toggle status aktif dokumen.

---

## Struktur Folder Utama

```
rag-engine/
├── app/
│   ├── main.py                 # Titik masuk (entrypoint) FastAPI & migrasi berkas bawaan
│   ├── api/routes/             # Router REST API (/chat, /config, /sources, /documents, /health)
│   ├── services/
│   │   ├── config_store.py      # Pengelolaan konfigurasi AI & Kredensial dinamis
│   │   ├── ingestion.py         # Parsing multi-format dokumen & injeksi ke ChromaDB
│   │   ├── retrieval.py         # Pencarian semantik (case-insensitive) & filter kategori
│   │   ├── generation.py        # Pembuatan prompt modular & interaksi Gemini API
│   │   ├── sharepoint_fetcher.py# Unduh file OneDrive/Sharepoint (Graph & Fallback)
│   │   ├── googledrive_fetcher.py # Parser & downloader Google Drive/Sheets
│   │   └── chat_store.py        # Pengelolaan database riwayat chat lokal
│   └── core/config.py          # Loader dynamic client Gemini & konstanta threshold
├── tests/                      # Unit dan integration test suite (Python unittest)
│   ├── test_ingestion.py       # Pengujian pemecahan kalimat dan parsing baris Excel
│   ├── test_stores.py          # Pengujian lifecycle config store & source store
│   └── test_api_routes.py      # Pengujian endpoint REST API FastAPI
├── data/
│   ├── config_store.json       # Database konfigurasi kredensial (Grouped-Candidate)
│   ├── sources_store.json      # Database kategori sync SharePoint terdaftar
│   ├── documents_store.json    # Database list metadata file manual terdaftar
│   ├── conversations.json      # Database riwayat chat lengkap
│   ├── documents/              # Penyimpanan fisik file manual (ada berkas contoh)
│   └── vector_store/           # Database biner ChromaDB (vektor indeks)
├── frontend/
│   ├── app/
│   │   ├── page.js             # Kontainer SPA utama (Tab Obrolan & Konfigurasi)
│   │   ├── ChatInterface.js    # Area interface tanya jawab & referensi dokumen
│   │   ├── ConfigManager.js    # Pengelolaan dinamis API Key & kredensial
│   │   ├── DocumentManager.js  # Area drag-and-drop manual upload file
│   │   └── OneDriveManager.js  # Panel CRUD kategori sync cloud drive
│   └── package.json            # Daftar dependencies NodeJS
├── .dockerignore               # Aturan pengecualian context build Docker
├── docker-compose.yml          # Konfigurasi container orkestrasi Docker
└── README.md                   # Panduan dokumentasi proyek (file ini)
```

---

## Fitur Unggulan Tambahan
- **Smart Rate Limiting**: Membatasi laju request embedding agar tidak melebihi kapasitas Gemini API Free Tier (maksimal 15 RPM) dengan mekanisme *exponential backoff* otomatis saat mendeteksi `RESOURCE_EXHAUSTED`.
- **Row-by-Row Tabular Parsing**: Pemecahan berkas spreadsheet (`.xlsx`, `.csv`) dilakukan per baris agar setiap informasi baris menjadi satu kesatuan dokumen utuh di database vektor.
- **Multimodal OCR**: Mendukung unggahan gambar (`.png`, `.jpg`, `.jpeg`, `.webp`), di mana sistem menggunakan kemampuan multimodal Gemini untuk membaca teks dan menganalisis visual sebelum disimpan.
- **WIB Time-Aware Prompting**: Menyertakan konteks waktu WIB (Waktu Indonesia Barat) ke dalam system prompt agar AI dapat menganalisis referensi waktu seperti "bulan lalu" atau "kemarin" secara akurat.
- **Session & Pinned Chats**: Riwayat chat dapat dihapus, disematkan (*pinned*), dan diganti namanya secara dinamis.

