# NOTULENSI LENGKAP & DOKUMEN HANDOVER PROYEK: TPS RAG ENGINE

**Tanggal Handover:** 7 Agustus 2026  
**Penulis:** Muhammad Raynar Hammam (Peserta Magang)  
**Institusi:** PT Terminal Petikemas Surabaya (TPS) — Anak perusahaan Pelindo  
**Status Proyek:** Siap Diuji (Fase Belajar - Stabil)  
**Tumpukan Teknologi:** Next.js (frontend) + FastAPI/Python (backend) + ChromaDB (vector store lokal) + Gemini (embedding & generation)

---

## 1. KONTEKS & LATAR BELAKANG PROYEK

Proyek **TPS RAG Engine** adalah proyek magang ketiga setelah proyek *TPS Smart Attendance* dan *TPS APD Detection*. Proyek ini dirancang sebagai chatbot internal organisasi yang mampu menjawab pertanyaan berdasarkan dokumen rahasia/dokumen kerja perusahaan (bukan pengetahuan umum AI). 

### Dua Jenis Sumber Data:
1. **Upload Manual (File Lokal):** Mengunggah berkas secara langsung (`.pdf`, `.docx`, `.xlsx`, `.csv`, `.pptx`, dan berkas gambar `.png`/`.jpg`).
2. **OneDrive/SharePoint Integration (Per Kategori):** Menghubungkan satu kategori pencarian khusus (contoh: kategori "Overview Box") ke satu file Excel spreadsheet tertentu di SharePoint tenant organisasi TPS.

### Fitur Kategori (Navigasi Scope):
Tujuan utama dari pengelompokan data berdasarkan kategori ini adalah agar pencarian jawaban dibatasi (*scoped*) ke dalam satu kategori dokumen saja yang dipilih pengguna melalui combo box di navbar. Hal ini mencegah sistem melakukan kueri ke seluruh basis dokumen secara acak, yang berdampak pada **penghematan konsumsi token** dan **akurasi jawaban (presisi) yang jauh lebih tinggi**. Ini adalah instruksi langsung dari mentor proyek.

### Alur Kerja Pengembangan:
Pengembangan dilakukan dengan pendekatan **vibe coding**, di mana pengembang menulis prompt terperinci secara interaktif, dan AI coding assistant (seperti Claude Code atau Cursor) melakukan modifikasi kode langsung pada workspace lokal.

---

## 2. STATUS SAAT INI (PENCAPAIAN SISTEM)

### A. Komponen Backend (FastAPI)
- **Sistem Kategori Dinamis:** CRUD kategori berjalan penuh melalui REST API dan UI (tidak di-hardcode).
- **Dual-Path Sync SharePoint:**
  1. **Jalur Resmi (Microsoft Graph API):** Menggunakan token OAuth dengan model autentikasi kredensial klien Azure AD (*tenant_id*, *client_id*, *client_secret*).
  2. **Jalur Fallback:** Otomatis aktif jika kredensial Azure kosong, dengan memodifikasi query parameter link sharing OneDrive/SharePoint publik (`&download=1`).
- **Ingestion Pipeline:** Proses parsing berkas, kalimat/baris chunking, kalkulasi embedding (`text-embedding-004`), dan injeksi data ke database vektor ChromaDB dengan menyematkan metadata `"category"` dan `"source"`.
- **Modul Retrieval:** Mendukung pemfilteran berbasis kategori (SharePoint) atau nama file dokumen (manual).
- **Dynamic Config Store:** Manajemen kredensial API key Gemini, model AI, dan Azure AD dengan skema *candidate/active*. Nilai konfigurasi dapat diganti secara langsung via UI tanpa perlu mematikan/restart server.

### B. Komponen Frontend (Next.js)
- **Navbar Category Selector:** Combo box dinamis ("Sumber Data: Semua Data ▾") untuk memilih lingkup dokumen.
- **Modal Tata Kelola Data:** Tab terpisah untuk "OneDrive SharePoint" dan "Dokumen Manual".
- **Halaman Konfigurasi:** Tab "Umum" (antarmuka uji coba obrolan) dan tab "Tata Kelola" (pengaturan API key Gemini, Azure AD Tenant, Client ID, dan Client Secret).
- **Label Navigasi Bersih:** Telah diperbaiki menjadi **Chat**, **Sumber Data**, dan **Konfigurasi**.

### C. Hasil Validasi & Blocker Uji Coba
- **Upload Manual (Sukses):** Pengunggahan manual berhasil divalidasi (misal file `CV_Muhammad Raynar Hammam.pdf` terindeks sebanyak 32 chunk).
- **Error Handling & Fallback (Sukses):** Logs Docker backend mencatat `has_valid_azure_credentials=False` dan berhasil masuk ke metode `fallback_download`. Sistem mendeteksi file HTML pengalihan login secara akurat untuk mencegah korupsi data.
- **Blocker Utama (Kredensial SharePoint):** Sinkronisasi cloud OneDrive/SharePoint menggunakan link asli tenant TPS masih terhambat. Kebijakan keamanan tenant TPS memblokir hak berbagi data ke luar organisasi/anonim (*Sharing is limited on this item — you can only copy links for people who have existing access*). 
- **Solusi Blocker:** Wajib menggunakan kredensial **Microsoft Azure App Registration** resmi yang memiliki izin akses `Files.Read.All` atau `Sites.Read.All`. Saat ini, kredensial tersebut masih menggunakan placeholder di database (`azure_graph_placeholder`) karena belum diberikan oleh tim IT TPS.

---

## 3. ARSITEKTUR KODE BACKEND (`app/`)

### A. Entrypoint & Core Config
- **[app/main.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/main.py):** Titik masuk server FastAPI. Memuat middleware CORS dan mendaftarkan router API. Menyediakan fungsi `_migrate_legacy_documents()` yang dijalankan sekali saat startup untuk melakukan registrasi ulang chunk ChromaDB lama ke file `documents_store.json` jika database registrasi manual terdeteksi kosong.
- **[app/core/config.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/core/config.py):** Pengendali konfigurasi dinamis. Fungsi `get_gemini_api_key()`, `get_embedding_model()`, dan `get_generation_model()` mengambil nilai secara langsung dari *config store* di setiap request. Panggilan client AI menggunakan thread-local cache (`get_gemini_client()`) untuk keamanan konkurensi. Di file ini juga didefinisikan parameter utama:
  - `TOP_N = 15`: Dinaikkan dari 3 agar pertanyaan agregasi spreadsheet memperoleh jumlah potongan baris yang memadai.
  - `DISTANCE_THRESHOLD = 0.70`: Ambang batas kemiripan vektor. Vektor dengan jarak distansi di atas `0.70` akan diabaikan karena dianggap tidak relevan.

### B. Router API (`app/api/routes/`)
- **[health.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/health.py):** Endpoint `GET /health` untuk memantau status kesehatan sistem, ketersediaan koneksi ChromaDB, jumlah total chunk terindeks, dan status model AI aktif.
- **[config.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/config.py):** Menyediakan rute GET/POST/PUT/PATCH(activate)/DELETE untuk konfigurasi. Endpoint `/config/{key}/reveal` digunakan untuk memunculkan nilai rahasia (seperti API key asli) yang disamarkan oleh UI.
- **[documents.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/documents.py):** Mengelola dokumen manual. Proses upload file menggunakan skema transaksi 3 fase: *Save file fisik* $\rightarrow$ *Ingest ke ChromaDB* $\rightarrow$ *Register ke dokumen store*. Jika salah satu fase gagal, sistem akan menghapus kembali file fisik dan indeks vektor di ChromaDB.
- **[sources.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/sources.py):** Mengelola kategori OneDrive/SharePoint. Endpoint `/sources/{id}/sync` membuat direktori sementara via `tempfile.TemporaryDirectory()`, mengunduh file spreadsheet, mengindeksnya dengan tag kategori, dan menghapus direktori sementara setelah selesai.
- **[chat.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/chat.py):** Menerima pesan pertanyaan dan filter kategori dari frontend, memanggil pencarian similarity, mengumpankan hasilnya ke Gemini, menyimpan pesan obrolan, dan mengembalikan jawaban beserta sumber dokumen referensi.
- **[conversations.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/api/routes/conversations.py):** Menyediakan REST API CRUD untuk mengelola riwayat sesi chat di panel navigasi samping.

### C. Services Layer (`app/services/`)
- **[ingestion.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/ingestion.py):** Jantung pemrosesan dokumen.
  - **Txt/Docx/Pdf/Pptx Parsers:** Memecah teks dengan fungsi `chunk_by_sentences()` menggunakan batas kalimat hingga mencapai panjang sekitar `300` karakter.
  - **Excel/CSV Parser:** Menggunakan fungsi `_dataframe_to_chunks()`. **Strategi Kunci:** 1 baris baris data diubah menjadi string format kunci-nilai (`Kolom: Nilai`). Satu baris mewakili satu fakta mandiri di database vektor.
  - **Image Parser (OCR):** Mengirim file gambar ke Gemini Vision API dengan prompt OCR terstruktur, lalu memecah teks hasil pembacaan gambar.
  - **Batching & Rate-Limiter:** Fungsi `_embed_texts_batch()` menggunakan ThreadPoolExecutor untuk pemrosesan batch paralel, tetapi dibatasi lajunya dengan mekanisme jendela sliding time (`MAX_RPM = 12`) untuk memproteksi batas RPM gratisan Gemini.
  - **Pembersihan Data Lama:** Sebelum menyimpan chunk dokumen baru, data lama dengan nama file yang sama dihapus terlebih dahulu (`collection.delete(where={"source": filename})`) untuk menghindari duplikasi data.
- **[retrieval.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/retrieval.py):** Mengubah query input menjadi representasi vektor (`RETRIEVAL_QUERY`) lalu melakukan kueri database vektor.
  - *Pemfilteran Kategori:* Menggunakan normalisasi *case-insensitive* dan *trimmed whitespace*. Jika `category` sama dengan nama file manual $\rightarrow$ filter `source`. Jika `category` sama dengan kategori OneDrive $\rightarrow$ filter `category`. Jika kosong atau `"Semua Data"` $\rightarrow$ filter `source` dibatasi hanya pada daftar nama file manual yang aktif saja.
- **[generation.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/generation.py):** Memformulasikan prompt RAG secara modular dengan fungsi helper `get_wib_formatted_date()`. Menyertakan waktu terkini dalam zona WIB (UTC+7) ke dalam system prompt untuk menginterpretasikan kata waktu relatif ("bulan lalu", "tahun ini") serta panduan penanganan data tabel.
- **[chat_store.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/chat_store.py):** Mengelola berkas database JSON `data/conversations.json`. Secara otomatis memotong 40 karakter pertama pesan pengguna sebagai judul percakapan baru.
- **[config_store.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/config_store.py):** Menyediakan fungsi database konfigurasi dengan proteksi tidak boleh menghapus kandidat terakhir dalam suatu grup konfigurasi.
- **[sharepoint_fetcher.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/app/services/sharepoint_fetcher.py):** Mengunduh file dari cloud. Jika kredensial Azure AD terisi, sistem akan melakukan request token dan mengurai URL berbagi OneDrive ke representasi API `u!{base64url}`. Jika kosong, sistem menggunakan tautan modifikasi langsung. Seluruh proses validasi berkas dilakukan menggunakan modul `pandas.read_excel()`.

### D. Unit Testing Suite (`tests/`)
- **[tests/test_ingestion.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/tests/test_ingestion.py):** Pengujian unit untuk fungsi pemecahan kalimat dan konversi baris DataFrame menjadi potongan chunk.
- **[tests/test_stores.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/tests/test_stores.py):** Pengujian lifecycle aktivasi kandidat konfigurasi, proteksi penghapusan, dan reset status sinkronisasi.
- **[tests/test_api_routes.py](file:///Users/muhammadraynar/Documents/MAGANG%20TPS/rag-engine/tests/test_api_routes.py):** Pengujian integrasi endpoint FastAPI menggunakan TestClient (/health, /config, /documents, /sources).

---

## 4. ARSITEKTUR FRONTEND (`frontend/app/`)

- **layout.js & NavLinks.js:** Kerangka layout SPA (Single Page Application) dan penyedia tautan navigasi.
- **globals.css:** Mengatur tema warna organisasi: Navy Pelindo `#0B2F5C` (warna utama) dan Accent Blue `#2B7FD6` (warna tombol/link).
- **CategoryContext.js & CategorySelector.js:** Pengelola status kategori pencarian terpilih di navbar. Category selector otomatis membaca seluruh kategori OneDrive yang status sinkronisasinya sukses beserta berkas manual yang aktif.
- **DataManagementModal.js:** Dialog popup untuk mengelola sumber data, menampung komponen `OneDriveManager` dan `DocumentManager`.
- **OneDriveManager.js:** Form input registrasi tautan OneDrive/SharePoint dan tabel monitoring status sinkronisasi. Menyertakan lencana visual (*badge*) mode sinkronisasi aktif: "Mode: Fallback" atau "Mode: Graph API" berdasarkan data kembalian backend.
- **DocumentManager.js:** Mengelola upload manual via drag-and-drop dan menampilkan tabel file beserta status aktifnya.
- **ChatInterface.js:** Antarmuka chatbot interaktif, digunakan pada halaman utama aplikasi dan tab simulasi cepat di halaman konfigurasi.
- **ConfigManager.js:** Mengelola parameter kunci API Gemini dan input kredensial rahasia Azure AD.

---

## 5. CONCERN UTAMA & LIMITASI SISTEM SAAT INI

Bagi pengembang atau AI yang akan melanjutkan proyek ini, harap perhatikan poin-poin krusial berikut:

1. **Batas Gemini API RPM:** Penggunaan model gratisan rawan terkena limitasi server. Jika memproses sinkronisasi dokumen Excel baris besar, pastikan rate limiter di backend dikonfigurasi dengan aman.
2. **Penyimpanan Lokal JSON:** Database konfigurasi, riwayat chat, dan metadata OneDrive hanyalah file JSON teks biasa (`data/`). File-file ini rentan mengalami masalah konkurensi tulis jika diakses banyak user secara simultan.
3. **Persistensi ChromaDB:** ChromaDB berjalan secara lokal di dalam folder container backend. Jika server dipindahkan ke platform serverless container (seperti Cloud Run), data vektor ChromaDB akan terhapus karena sifat sistem serverless yang stateless.
4. **Kebijakan Tenant SharePoint TPS:** Kebijakan ini diblokir pada tingkat admin tenant IT Pelindo/TPS. Jangan membuang waktu mencoba melakukan bypass tautan OneDrive personal atau memodifikasi parameter URL; solusi satu-satunya adalah menggunakan otorisasi Azure AD.

---

## 6. RENCANA PENGEMBANGAN MASA DEPAN (ROADMAP)

1. **Migrasi Database Produksi:** Memindahkan penyimpanan file JSON lokal dan ChromaDB lokal ke **Supabase** (dengan ekstensi pgvector) atau PostgreSQL mandiri untuk kesiapan deployment multi-user.
2. **Integrasi Saluran Komunikasi (Bot):** Menghubungkan endpoint `/chat` dengan platform pihak ketiga seperti bot WhatsApp Business API dan Telegram Bot.
3. **Evaluasi Otomatis (Ragas):** Mengintegrasikan framework pengujian RAG seperti Ragas untuk memantau metrik relevansi dokumen (*Context Recall*) dan kebenaran jawaban AI (*Faithfulness*).
4. **Semantic Chunking:** Mengubah pemotongan teks statis (300 karakter) menjadi pembagian berbasis makna paragraf menggunakan analisis tingkat perbedaan semantik kalimat.

---

## 7. KUMPULAN PERTANYAAN UJI COBA VALIDASI

Untuk memvalidasi kualitas sistem RAG setelah melakukan pembaruan, jalankan kueri pengujian menggunakan file data asli **OVERVIEW_BOX_DOMESTIK.csv** (memiliki data dari rentang waktu Januari 2023 - Februari 2025):

- **Uji Detail Baris:** *"Berapa TEUS untuk LOP TIL pada Januari 2023?"*  
  $\rightarrow$ Jawaban Benar: **4.170**
- **Uji Nilai Maksimum:** *"Berapa TEUS tertinggi yang pernah tercatat, dan kapan?"*  
  $\rightarrow$ Jawaban Benar: **47.565 TEUS, LOP TIL, Desember 2024**
- **Uji Agregasi Nilai (Uji Kapasitas TOP_N):** *"Berapa total TEUS LOP TIL sepanjang tahun 2023?"*  
  $\rightarrow$ Jawaban Benar: **35.686** (sistem harus berhasil menarik 12 baris data tahun 2023 dan menjumlahkannya secara tepat).
- **Uji Nilai Kosong / Simbol Strip:** *"Ada baris TAS bulan Mei 2024, nilainya berapa?"*  
  $\rightarrow$ Jawaban Benar: **0** (pada berkas CSV ditulis dengan simbol `-`, sistem harus mampu menginterpretasikan simbol tersebut sebagai angka nol).
- **Uji Rentang Batas Data:** *"Sampai bulan apa data 2025 tercatat?"*  
  $\rightarrow$ Jawaban Benar: **Hanya sampai Februari 2025**.

---

## 8. ALUR KERJA PENGEMBANGAN (DEVELOPER NOTES)

- **Direktori Utama:** Seluruh perintah Python harus merujuk ke root folder workspace `/Users/muhammadraynar/Documents/MAGANG TPS/rag-engine/` sebagai basis kerja.
- **Masalah Cache Docker:** Jika Anda menambahkan pustaka baru di `requirements.txt` atau `package.json`, Anda **wajib** menjalankan perintah build ulang secara penuh:  
  ```bash
  docker compose down && docker compose up --build
  ```
  Menjalankan perintah `docker compose up` tanpa parameter `--build` akan membuat Docker menggunakan layer container lama yang telah ter-cache, sehingga perbaikan kode Anda tidak akan teraplikasikan di dalam container.
- **Keamanan Data:** Berkas di dalam folder `data/` (terutama `config_store.json` yang memuat API key) bersifat rahasia dan sudah terdaftar di `.gitignore`. Jangan pernah men-commit file tersebut ke repositori publik.
- **Konfigurasi Git Email:** Pastikan konfigurasi `git config user.email` di komputer lokal Anda sesuai dengan email utama yang terdaftar pada akun GitHub Anda agar riwayat kontribusi terbaca di grafik profil kontributor GitHub.
