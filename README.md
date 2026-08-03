# TPS RAG Engine

Proyek mesin pencari pintar berbasis **RAG (Retrieval-Augmented Generation)** menggunakan Next.js (frontend), FastAPI (backend), ChromaDB (vector store lokal), dan Gemini (embedding & text generation). 

Sistem ini mendukung pencarian dokumen berdasarkan kategori dinamis yang tersinkronisasi langsung dari folder/berkas Excel di **SharePoint/OneDrive TPS** serta dokumen yang diunggah secara manual.

---

## 🛠️ Persyaratan Sistem & Instalasi

Ada dua cara untuk menjalankan proyek ini: menggunakan **Docker** (Sangat Direkomendasikan) atau **Manual Setup**.

### Cara 1: Menggunakan Docker (Rekomendasi & Instan)

Anda hanya perlu memasang **Docker & Docker Desktop** di komputer Anda.

1. **Clone & Masuk ke Folder Project**
   ```bash
   git clone https://github.com/mraynar/rag-engine.git
   cd rag-engine
   ```

2. **Jalankan Project dengan Docker Compose**
   ```bash
   docker compose down && docker compose up --build
   ```
   *Perintah ini otomatis mengunduh dependencies, membangun container backend (FastAPI, port `8000`) dan frontend (Next.js, port `3000`), lalu menjalankannya secara paralel.*

3. **Akses Aplikasi**
   - **Frontend UI:** [http://localhost:3000](http://localhost:3000)
   - **Backend API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Cara 2: Manual Setup (Tanpa Docker)

Jika Anda ingin menjalankan atau memprogram ulang service di luar container:

#### A. RUN BACKEND (FastAPI)
1. Masuk ke folder root `rag-engine/` dan buat virtual environment Python:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Untuk Windows: venv\Scripts\activate
   ```
2. Install package pendukung dari `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
3. Jalankan server FastAPI dengan Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

#### B. RUN FRONTEND (Next.js)
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
   Aplikasi Next.js akan berjalan di [http://localhost:3000](http://localhost:3000).

---

## ⚙️ Langkah Konfigurasi Kredensial AI & Azure AD (Live UI)

Sistem ini menggunakan penyimpanan konfigurasi dinamis (`data/config_store.json`), sehingga **TIDAK memerlukan restart server** saat Anda memperbarui API Key atau kredensial.

Setelah web terbuka di `http://localhost:3000`, klik tab **"Konfigurasi"** di atas untuk mengatur parameter berikut:

1. **Gemini API Key (Wajib)**
   - Tambah kandidat baru dengan memasukkan kunci API Anda (didapat dari Google AI Studio).
   - Klik tombol **"Aktifkan"** pada kandidat tersebut.
2. **Kredensial Azure / Microsoft Graph API (Opsional untuk Sync SharePoint Resmi)**
   - Jika Anda memiliki Azure App Registration di organisasi TPS, masukkan:
     - `AZURE_TENANT_ID`
     - `AZURE_CLIENT_ID`
     - `AZURE_CLIENT_SECRET` (Pastikan menginput *Value-nya*, bukan Secret ID).
   - Konfirmasi permission pada registrasi Azure tersebut tipe **Application** dengan akses **`Files.Read.All`** atau **`Sites.Read.All`** dan sudah disetujui (*admin consent*).
   - Klik **"Aktifkan"** setelah disimpan.

---

## 📂 Alur Manajemen Sumber Data (Syncing Data)

1. Buka dropdown **"Sumber Data: Semua Data"** di bagian kanan atas navbar.
2. Klik tombol **"Kelola Sumber Data"** di bagian paling bawah untuk memunculkan modal overlay.
3. Di modal tersebut, Anda memiliki 2 tab utama:
   - **OneDrive SharePoint:** Daftarkan kategori baru dan masukkan link sharing OneDrive Anda (file `.xlsx` spreadsheet).
     - *Catatan Sync:* Jika kredensial Azure di atas **belum diisi**, sistem otomatis menggunakan **Fallback mode** (`&download=1`). Pastikan link dibuat lewat tombol **Share > Copy Link** di SharePoint dengan izin akses publik (*Anyone with the link*).
   - **Dokumen Manual:** Unggah berkas dokumen Anda secara manual (`.pdf`, `.docx`, `.txt`, `.xlsx`) sebagai alternatif sekunder.
4. Klik tombol **Sync** pada baris kategori yang baru dibuat untuk mengekstrak, memecah (*chunking*), membuat embedding, dan mengindeks data ke database vektor.

---

## 🏗️ Struktur Folder Utama

```
rag-engine/
├── app/
│   ├── main.py                 # Titik masuk (entrypoint) FastAPI
│   ├── api/routes/             # Router endpoint /chat, /config, dan /sources
│   ├── services/
│   │   ├── sharepoint_fetcher.py # Logic download SharePoint (Graph API & Fallback)
│   │   ├── config_store.py      # Pengelolaan API Key & Kredensial dinamis
│   │   ├── retrieval.py         # Pencarian semantik dan filtering kategori
│   │   └── ingestion.py         # Parsing dokumen excel/pdf dan simpan ke ChromaDB
│   └── core/config.py          # Loader dynamic client Gemini & Azure
├── data/
│   ├── config_store.json       # Database kredensial (Grouped-Candidate)
│   ├── sources_store.json      # Database link SharePoint kategori terdaftar
│   └── documents/              # Dokumen lokal untuk upload manual
├── frontend/
│   ├── app/
│   │   ├── page.js             # Layout SPA dengan tab Umum & Konfigurasi
│   │   ├── CategorySelector.js # Combo box pemilih kategori di navbar
│   │   ├── DataManagementModal.js # Modal manajemen OneDrive & Manual upload
│   │   └── ChatInterface.js    # Tampilan antarmuka chat dengan chatbot
│   └── package.json            # Daftar NodeJS packages
├── docker-compose.yml          # Konfigurasi container orkestrasi docker
└── README.md                   # Panduan dokumentasi proyek
```
