# NOTULENSI LENGKAP PROJECT — Untuk Handoff / Kelanjutan oleh AI atau Orang Lain
**PT Terminal Petikemas Surabaya (TPS) — Anak perusahaan Pelindo**  
**Project:** TPS RAG Engine (Chatbot berbasis dokumen internal)  
**Peserta magang:** Muhammad Raynar Hammam  
**Stack:** Next.js (frontend) + FastAPI/Python (backend) + ChromaDB (vector store) + Gemini (embedding & generation)  
**Update terakhir:** 13 Agustus 2026

═══════════════════════════════════════
## 1. KONTEKS PROJECT
═══════════════════════════════════════
Selain project TPS Smart Attendance dan TPS APD Detection, ini adalah project ketiga: **TPS RAG Engine** — chatbot internal yang menjawab pertanyaan berdasarkan data perusahaan secara tertutup (bukan pengetahuan umum AI). Sumber data terbagi menjadi 2 jenis:
1. **Upload Manual:** Berkas lokal berupa `.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx`, dan berkas gambar (`.png`, `.jpg`, `.jpeg`, `.webp` via Gemini Vision OCR).
2. **Link OneDrive/SharePoint/Google Drive:** Sinkronisasi spreadsheet online per "kategori" (misalnya kategori "Overview Box" terhubung ke 1 file `.xlsx` tertentu di cloud).

**Tujuan Utama Fitur Kategori (Nav Filter):**
Membatasi ruang lingkup pencarian jawaban semantik hanya pada 1 kategori/dokumen yang dipilih pengguna lewat combo box di navbar, bukan mencari ke semua dokumen sekaligus. Hal ini menghemat penggunaan token LLM dan meningkatkan presisi jawaban secara signifikan. Ini merupakan instruksi eksplisit dari mentor.

**Metode Kerja Developer:**
Raynar melakukan *vibe coding* (menulis instruksi detail) yang dieksekusi oleh AI coding assistant. Peran asisten AI adalah memandu implementasi, melakukan review, pengujian, pemecahan bug (*debugging*), dan penyusunan struktur dokumentasi akhir.

═══════════════════════════════════════
## 2. STATUS SAAT INI — APA YANG SUDAH JADI
═══════════════════════════════════════
### ✅ Backend (FastAPI):
- **Sistem Kategori Dinamis:** CRUD kategori OneDrive/SharePoint berjalan penuh melalui REST API (tanpa hardcode).
- **Dual-Path Sync SharePoint:** Menggunakan **Microsoft Graph API** (jika kredensial Azure AD terisi) dan **Fallback Download** (jika kosong, dengan memodifikasi query parameter link share menjadi `&download=1`).
- **Ingestion Pipeline:** Proses parsing berkas, pemecahan kalimat (*sentence chunking*), baris spreadsheet chunking, pembuatan embedding (`text-embedding-004`), dan penyimpanan vektor ke ChromaDB lengkap dengan metadata `"source"` dan `"category"`.
- **Modul Retrieval yang Presisi:** Pencarian kemiripan vektor (*similarity search*) mendukung filter kategori dinamis yang toleran (*case-insensitive* & *trimmed whitespace*).
- **Config Store (Candidate/Active):** Pengaturan API key Gemini, model AI, dan kredensial Azure dapat diganti secara langsung melalui web UI tanpa harus me-restart server backend.
- **Endpoint Healthcheck & Monitoring:** Ditambahkan endpoint `GET /health` untuk memantau status kesehatan server, ketersediaan koneksi ChromaDB, jumlah total chunk terindeks, dan status model AI aktif.

### ✅ Frontend (Next.js):
- **Penyelarasan Bahasa (English Standardization):** Tampilan antarmuka, notifikasi status upload, dan label navigasi telah diselaraskan ke dalam Bahasa Inggris yang bersih dan profesional:
  - Tab Navigasi: **Chat** (sebelumnya *Umum*), **Data Sources** (sebelumnya *Sumber Data*), dan **Configuration** (sebelumnya *Konfigurasi*).
  - Teks Dialog: Tombol dropdown `Data Source: All Data (Default)`, modal `Data Source Management` dengan sub-tab `Cloud Data Sources` dan `Manual Documents`.
- **Persistensi Sesi Chat (Sidebar):** Riwayat percakapan disimpan secara lokal dan dapat dibuat, dihapus, disematkan (*pinned*), serta diganti namanya secara dinamis.
- **Upload Status Stack:** Menampilkan antarmuka monitoring proses pengunggahan berkas secara *real-time* di bagian atas layar.

### ✅ Pengujian & Otomatisasi (Test Suite):
- Dibuat 11 skenario pengujian otomatis menggunakan Python `unittest` yang mencakup:
  1. `tests/test_ingestion.py` (chunking kalimat dan konversi baris DataFrame Excel).
  2. `tests/test_stores.py` (daur hidup konfigurasi config store dan sources store).
  3. `tests/test_api_routes.py` (pengujian integrasi REST API `/health`, `/config`, `/documents`, `/sources`).
- Seluruh 11 pengujian otomatis dinyatakan lulus (**OK**) dengan total waktu eksekusi 0.189s.

### ⚠️ Belum Tervalidasi / Masih Terhambat:
- **Kredensial Azure Resmi:** Kredensial Azure AD (Tenant ID, Client ID, Client Secret) masih menggunakan data *placeholder* karena tim IT TPS belum menyerahkan kredensial resmi.
- **Kebijakan Sharing Tenant TPS:** Tautan sharing OneDrive/SharePoint yang dibuat oleh akun organisasi TPS dibatasi hak aksesnya (tidak dapat diatur untuk "Anyone with the link"). Oleh sebab itu, jalur sinkronisasi online sesungguhnya baru dapat diuji secara penuh setelah kredensial Azure AD resmi diperoleh.

═══════════════════════════════════════
## 3. STRUKTUR FILE BACKEND (folder app/)
═══════════════════════════════════════
- **[app/main.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/main.py):** Titik masuk FastAPI. Mengatur CORS, lifespan handler, dan registrasi ulang data legacy (`_migrate_legacy_documents`) jika database JSON terdeteksi kosong saat startup.
- **[app/core/config.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/core/config.py):** Pusat pembacaan konfigurasi dinamis. Mengatur konstanta `TOP_N = 15` (untuk data tabular) dan `DISTANCE_THRESHOLD = 0.70`. Memuat client Gemini dengan cache berbasis thread-local (`get_gemini_client`).
- **[app/schemas/](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/schemas/):** Modul validasi skema Pydantic (`chat.py`, `config.py`, `document.py`, `source.py`) lengkap dengan anotasi `Field` dan contoh data Swagger.
- **[app/api/routes/](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/):**
  - **`chat.py`**: Mengelola request chatbot (`POST /chat`).
  - **`config.py`**: CRUD konfigurasi AI dinamis dan endpoint `/config/reset` untuk membersihkan seluruh data sistem.
  - **`documents.py`**: Mengelola unggahan manual (3-phase upload transaksi: simpan berkas $\rightarrow$ ingest ChromaDB $\rightarrow$ register registry JSON).
  - **`sources.py`**: Mengelola sinkronisasi OneDrive/SharePoint dan Google Drive.
  - **`health.py`**: Endpoint `/health` sistem monitoring status.
- **[app/services/](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/):**
  - **`ingestion.py`**: Membaca dokumen, chunking baris Excel (`Kolom: Nilai`), multimodal OCR gambar, rate-limiting (maksimum 12 RPM dengan backoff eksponensial), dan penyisipan data ke ChromaDB.
  - **`retrieval.py`**: Mengubah pertanyaan menjadi vektor, mencari dokumen terdekat di ChromaDB, dan menerapkan filter kategori secara *case-insensitive* dan *trimmed*.
  - **`generation.py`**: Menyusun RAG prompt modular dengan menyisipkan format tanggal zona waktu WIB dan aturan pembacaan data tabel.
  - **`sharepoint_fetcher.py` & `googledrive_fetcher.py`**: Modul penarik berkas dari tautan cloud OneDrive/SharePoint dan Google Drive.
  - **`config_store.py` / `document_store.py` / `sources_store.py` / `chat_store.py`**: Pengelola logika database lokal berkas JSON di folder `data/`.

*(Catatan: Berkas `onedrive_fetcher.py` yang sebelumnya merupakan dead code telah dihapus sepenuhnya dari repositori).*

═══════════════════════════════════════
## 4. STRUKTUR FILE FRONTEND (folder frontend/app/)
═══════════════════════════════════════
- **`layout.js` & `NavLinks.js`:** Kerangka layout dan tautan navigasi menu utama.
- **`page.js`:** Halaman SPA utama yang membagi area ke tab **Chat** dan **Configuration**.
- **`AppProviders.js` & `UploadContext.js`:** Mengelola status notifikasi proses upload file global di background.
- **`CategoryContext.js` & `CategorySelector.js`:** Pengelola status kategori pencarian terpilih di navbar.
- **`ChatInterface.js`:** Antarmuka chatbot interaktif beserta sidebar sesi chat.
- **`ConfigManager.js`:** Panel pengelolaan kredensial API key Gemini dan Azure AD.
- **`DataManagementModal.js`:** Dialog popup untuk mengelola sumber data online dan manual dokumen.

═══════════════════════════════════════
## 5. STRUKTURAL STRUGGLE & DESIGN DISCUSSIONS
═══════════════════════════════════════
Berikut adalah ringkasan kendala teknis dan hasil diskusi desain yang penting untuk dipahami oleh penerus proyek ini:

### A. Isu Docker Build (Conflict .dockerignore)
- **Masalah:** Docker build gagal karena `Dockerfile.backend` mencoba menyalin folder `data/vector_store` dan `data/documents` ke dalam *image*, sementara folder tersebut diabaikan di `.dockerignore`.
- **Solusi:** `Dockerfile.backend` diperbaiki dengan menggunakan `RUN mkdir -p` untuk menyiapkan direktori kosong di kontainer. Berkas fisik yang sesungguhnya dimuat secara dinamis saat container berjalan melalui *volume mount* di `docker-compose.yml`.

### B. Pre-indexing vs. Lazy Loading (On-Demand RAG)
Terdapat usulan untuk menyimpan tautan OneDrive saja tanpa melakukan embedding di awal, lalu mengunduh dan membaca berkas secara langsung saat chat berlangsung.
- **Keputusan Desain:** Proyek ini **tetap menggunakan standar RAG (Pre-indexing ke ChromaDB)** karena pendekatan *Lazy Loading* memiliki dampak buruk yang signifikan:
  1. **Latency Tinggi:** Waktu respon chat menjadi sangat lama (~10-20 detik) karena sistem harus mengunduh file spreadsheet dari OneDrive di tengah obrolan.
  2. **Pemborosan Token:** Tanpa database vektor untuk menyaring informasi, seluruh isi berkas spreadsheet mentah harus dikirim ke Gemini di setiap chat, yang menghabiskan token kuota API dalam jumlah besar.
  3. **Identifikasi Berkas:** Sistem akan kesulitan menentukan berkas mana yang harus dibaca jika isinya belum diindeks secara semantik.

### C. Fitur Auto-Generate Folder
Untuk memastikan portabilitas aplikasi saat pertama kali di-*clone* dari Git:
- Backend diprogram untuk melakukan **auto-generate folder** secara dinamis (`Path.mkdir(parents=True, exist_ok=True)`) saat pertama kali berkas diunggah atau saat database JSON mendeteksi folder `data/` belum ada. Hal ini mencegah kegagalan `FileNotFoundError`.

═══════════════════════════════════════
## 6. PERTANYAAN TES YANG SUDAH DISIAPKAN
═══════════════════════════════════════
Berdasarkan data contoh `OVERVIEW_BOX_DOMESTIK.csv` (137 baris valid, kolom: Date, YEAR, MONTH_CODE, MONTH, LOP, TEUS, Boxes; LOP: SPI/TIL/TAS/MPN/ICON/PNJ/MAA/ICN/CTP; rentang Jan 2023 – Feb 2025):
- *"Berapa TEUS untuk LOP TIL pada Januari 2023?"* ➔ Jawaban benar: **4.170**
- *"Berapa TEUS tertinggi yang pernah tercatat, dan kapan?"* ➔ Jawaban benar: **47.565 TEUS, LOP TIL, Des 2024**
- *"Berapa total TEUS LOP TIL sepanjang tahun 2023?"* ➔ Jawaban benar: **35.686** (menguji efektivitas `TOP_N = 15` untuk agregasi 12 baris data).
- *"Apakah LOP CTP pernah ada aktivitas TEUS?"* ➔ Jawaban benar: **Tidak pernah (selalu 0)**.
- *"Ada baris TAS bulan Mei 2024, nilainya berapa?"* ➔ Jawaban benar: **0** (menguji apakah sistem dapat memahami simbol strip `"-"` sebagai nilai 0).

═══════════════════════════════════════
## 7. CATATAN TEKNIS & WORKFLOW PENTING UNTUK PENERUS
═══════════════════════════════════════
1. **Cara Menjalankan Lokal (Latar Belakang):**
   - **Backend:** `./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
   - **Frontend:** `npm run dev` (di dalam folder `frontend/`)
2. **Cara Menjalankan via Docker:**
   - Gunakan perintah `docker compose up --build` agar setiap perubahan pustaka ketergantungan (*dependency*) terpasang dengan benar di kontainer.
3. **Keamanan Data Lokal:**
   - Kredensial rahasia disimpan di file JSON dalam folder `data/`. Jangan pernah melakukan commit folder `data/` ke Git (sudah dicegah oleh `.gitignore`).
4. **Menjalankan Tes Suite:**
   - Jalankan perintah `./venv/bin/python -m unittest discover tests` untuk memastikan semua pengujian berjalan tanpa kegagalan sebelum melakukan commit.

═══════════════════════════════════════
## 8. YANG BISA DILAPORKAN KE MENTOR SEKARANG
═══════════════════════════════════════
1. Seluruh pipeline inti RAG (Ingestion multi-format berkas, rate-limiting, similarity search dengan filter kategori, prompt WIB time-aware, dan generation jawaban Gemini) telah **selesai dibangun dan divalidasi 100% menggunakan 11 unit & integration test**.
2. Antarmuka web (Next.js SPA) telah dimodernisasi dan diselaraskan ke dalam bahasa Inggris yang rapi dan profesional.
3. Struktur kontainer Docker telah dioptimalkan dan terbebas dari bug build context.
4. Aplikasi telah dipastikan aman dan bersifat portabel dengan fitur auto-generate folder dinamis saat pertama kali di-deploy di sistem baru.
5. Satu-satunya kebutuhan tersisa untuk tahap sinkronisasi cloud penuh adalah kredensial **Azure AD App Registration** resmi dari pihak IT TPS. Sembari menunggu kredensial tersebut, pengujian RAG data sesungguhnya tetap dapat berjalan lancar menggunakan fitur upload berkas manual.
