# AGENTS.md — RAG Engine (Learning Project)

> Dibaca oleh AI agent (Antigravity, dll) sebelum mengerjakan task di repo ini.

## 1. Ringkasan Project

Proyek belajar **RAG (Retrieval-Augmented Generation)** — TERPISAH TOTAL dari
`tps-smart-attendance` dan `apd-detection-tps`. Tujuan: memahami cara kerja RAG
dari nol (retrieval, embedding, augmented prompt, generation), sebelum nanti
dikembangkan jadi engine yang bisa dipakai banyak channel (Web, Mobile, WhatsApp).

**Prinsip fase ini:** belajar dulu pakai dokumen lokal sederhana, BUKAN langsung
ke database production. Sumber data retrieval bisa diganti ke database nanti
tanpa mengubah alur besar (retrieval → augmented → generation).

## 2. Stack

- Backend: **FastAPI** (Python) — 1 endpoint utama `POST /chat`
- LLM: **Gemini** (API key disimpan di tabel config, bukan hardcode/`.env` biasa
  — lihat poin 4)
- Vector store (fase belajar): **ChromaDB** lokal (file-based, simpel, tanpa
  setup database eksternal)
- Embedding: model embedding Gemini API (`text-embedding-004` atau versi
  terbaru — cek dokumentasi resmi saat implementasi, karena API model bisa berubah)

## 3. Role AI Agents

- **Retrieval Agent**: kerja di `app/services/retrieval.py` + `data/` — urus
  chunking dokumen, embedding, pencarian similarity
- **Generation Agent**: kerja di `app/services/generation.py` — urus format
  prompt akhir dan panggil Gemini API
- **API Agent**: kerja di `app/api/routes/` — endpoint tipis, panggil service,
  tidak boleh ada logic retrieval/generation langsung di sini
- **Config Agent**: satu-satunya yang boleh ubah skema tabel config
  (`app/services/config_store.py`) — lihat poin 4

## 4. Config Store (Key-Value, Generik)

Semua setting (API key, system prompt, nama model, dll) disimpan di 1 struktur
generik supaya bisa berkembang tanpa ubah skema:

| Kolom | Kegunaan |
|---|---|
| `key` | identifier unik, misal `gemini_api_key`, `system_prompt` |
| `description` | penjelasan kegunaan |
| `value` | isi setting |
| `is_secret` | true kalau harus disamarkan di UI (API key, dll) |

Fase belajar: boleh disimpan sebagai file JSON lokal (`data/config_store.json`).
Fase lanjut: pindah ke tabel database sungguhan (Postgres/Supabase project
TERPISAH dari `tps-smart-attendance` — JANGAN numpang ke Supabase project TPS).

## 5. Prinsip Umum

1. Repo ini independen — dependency (`requirements.txt`), `venv`, dan `.env`
   tidak boleh dicampur dengan project lain.
2. Endpoint API dirancang **channel-agnostic** — terima `{ "message": "..." }`,
   balas jawaban teks. Tidak ada logic khusus platform (Web/WA/Mobile) di
   backend inti; itu urusan masing-masing channel nanti.
3. API key TIDAK boleh hardcode di kode maupun di-commit ke git.
4. Progres bertahap: pastikan retrieval sederhana jalan dulu (dokumen lokal),
   baru pikirkan sumber data lebih kompleks.
