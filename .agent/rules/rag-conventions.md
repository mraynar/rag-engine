# RAG Conventions

## Alur Wajib (jangan diubah urutannya)
1. **Indexing** (sekali per dokumen baru): chunk dokumen → embedding → simpan
   ke vector store (`data/vector_store/`)
2. **Retrieval** (tiap ada pertanyaan): embedding pertanyaan → cari chunk
   paling mirip (cosine similarity) → ambil top-N (mulai dari N=3 untuk belajar)
3. **Augmented**: gabungkan chunk relevan + pertanyaan jadi 1 prompt
4. **Generation**: kirim prompt ke Gemini → kembalikan jawaban

## Dokumen Belajar
- Taruh file contoh (`.txt`/`.md`) di `data/documents/`
- Jangan taruh data sensitif/rahasia asli perusahaan di fase belajar ini

## Evaluasi Sederhana
- Saat belajar, selalu print/log: chunk mana yang terambil untuk tiap
  pertanyaan — supaya paham KENAPA jawaban tertentu muncul (debugging RAG
  sering soal retrieval yang salah ambil chunk, bukan soal LLM-nya)

## Reproducibility
- Kalau ganti model embedding, index ulang SEMUA dokumen (jangan campur
  embedding dari model berbeda dalam 1 vector store — dimensi/skalanya beda)
