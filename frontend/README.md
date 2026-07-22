# RAG Engine — Frontend

Antarmuka web untuk **TPS RAG Engine** — sistem tanya-jawab berbasis dokumen milik PT Terminal Petikemas Surabaya (Pelindo).

Dibangun dengan **Next.js 14** (App Router, JavaScript), terhubung ke backend FastAPI melalui REST API.

---

## Prasyarat

- Node.js ≥ 18
- Backend FastAPI sedang berjalan di **port 8000**

---

## Cara Menjalankan

### 1. Jalankan backend terlebih dahulu

Di direktori root repo (`rag-engine/`), aktifkan virtual environment lalu jalankan:

```bash
uvicorn app.main:app --reload
```

Backend akan berjalan di `http://127.0.0.1:8000`. Pastikan dokumen sudah diindeks sebelum mencoba fitur chat.

### 2. Jalankan frontend

Buka terminal baru, masuk ke folder `frontend/`:

```bash
cd frontend
npm install
npm run dev
```

Frontend akan berjalan di **http://localhost:3000**.

---

## Halaman

| Path | Fungsi |
|------|--------|
| `/` | Chat — tanya-jawab dengan dokumen yang sudah diindeks |
| `/config` | Konfigurasi — kelola API key, model, dan pengaturan sistem |

---

## Variabel Lingkungan

File `.env.local` sudah tersedia dengan nilai default:

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Jika backend berjalan di port atau host berbeda, ubah nilai ini sesuai kebutuhan.

---

## Catatan

- Frontend sepenuhnya **terpisah** dari backend — tidak ada shared code.
- Semua pemanggilan API menggunakan `NEXT_PUBLIC_API_URL` (tidak ada URL yang di-hardcode).
- Jika mengubah **API Key** di halaman Konfigurasi, backend **harus di-restart** agar perubahan berlaku.
