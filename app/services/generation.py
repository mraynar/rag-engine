from app.core.config import get_generation_model, get_gemini_client


def build_prompt(question: str, chunks: list[str]) -> str:
    context = "\n\n".join(chunks)
    return f"""Kamu adalah asisten AI yang menjawab pertanyaan HANYA berdasarkan konteks dokumen yang diberikan.

ATURAN WAJIB:
1. Gunakan HANYA data dari "Konteks" di bawah — jangan mengarang atau menggunakan pengetahuan luar.
2. Jika data tidak ada di konteks, jawab "Saya tidak menemukan informasi ini di dokumen."
3. Untuk pertanyaan yang membutuhkan perbandingan atau mencari nilai terbesar/terkecil (maksimum/minimum/terbanyak/tersedikit):
   - Baca SEMUA data yang tersedia di konteks dengan teliti.
   - Bandingkan SEMUA nilai yang relevan sebelum menentukan jawaban.
   - Cantumkan nilai dari SETIAP entri yang relevan agar perbandingan transparan.
   - Nyatakan jawaban akhir dengan jelas.
4. Untuk data tabular (tabel/spreadsheet), baca setiap baris secara sistematis sebelum menyimpulkan.
5. Format jawaban: gunakan **bold** untuk nama/istilah penting, bullet list untuk enumerasi, paragraf biasa untuk penjelasan.

Konteks:
{context}

Pertanyaan: {question}

Jawaban:"""


def generate_answer(prompt: str) -> str:
    response = get_gemini_client().models.generate_content(
        model=get_generation_model(), contents=prompt
    )
    return response.text
