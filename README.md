# RAG Engine (Learning Project)

Proyek belajar RAG (Retrieval-Augmented Generation) — terpisah dari
`tps-smart-attendance` dan `apd-detection-tps`.

## Struktur

```
rag-engine/
├── AGENTS.md                  # baca dulu sebelum coding
├── .agent/rules/
├── app/
│   ├── main.py                 # entry point FastAPI (belum dibuat)
│   ├── core/                   # config, koneksi Gemini
│   ├── api/routes/              # endpoint POST /chat
│   ├── services/
│   │   ├── retrieval.py         # chunking, embedding, similarity search
│   │   ├── generation.py        # panggil Gemini, susun prompt akhir
│   │   └── config_store.py      # kelola key-value config (API key, dll)
│   └── schemas/                 # Pydantic request/response
├── data/
│   ├── documents/                # dokumen contoh untuk belajar
│   └── vector_store/             # hasil indexing (gitignored)
├── .env.example
└── .gitignore
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn chromadb google-generativeai python-dotenv
cp .env.example .env   # isi GEMINI_API_KEY
```

## Alur Belajar (urutan pengerjaan)

1. Taruh 2-3 dokumen contoh di `data/documents/`
2. Bikin script indexing sederhana (chunk + embedding → simpan ke ChromaDB)
3. Bikin fungsi retrieval (pertanyaan → embedding → cari chunk mirip)
4. Gabungkan retrieval + panggil Gemini → `POST /chat` di FastAPI
5. Setelah paham alurnya, baru pikirkan sumber data lebih kompleks (database)
