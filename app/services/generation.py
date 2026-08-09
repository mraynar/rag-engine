from datetime import datetime, timezone, timedelta
from app.core.config import get_generation_model, get_gemini_client

_DAYS = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
_MONTHS = [
    "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]


def get_wib_formatted_date() -> str:
    """Return current date formatted in Indonesian locale with WIB (UTC+7) timezone."""
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz)
    day_name = _DAYS[now_wib.weekday()]
    month_name = _MONTHS[now_wib.month]
    return f"{day_name}, {now_wib.day} {month_name} {now_wib.year}"


def build_prompt(question: str, chunks: list[str]) -> str:
    """Build an augmented prompt combining contextual document chunks, system guidelines, and user question."""
    formatted_date = get_wib_formatted_date()
    context = "\n\n".join(chunks)

    return f"""Kamu adalah asisten AI yang menjawab pertanyaan HANYA berdasarkan konteks dokumen yang diberikan.

Konteks waktu saat ini: Hari ini adalah {formatted_date} (WIB).
Gunakan informasi ini untuk menafsirkan referensi waktu relatif dalam pertanyaan user, seperti "tahun ini", "tahun kemarin", "bulan lalu", "kemarin", dsb.

ATURAN WAJIB:
1. Gunakan HANYA data dari "Konteks" di bawah — jangan mengarang atau menggunakan pengetahuan luar.
2. Jika data tidak ada di konteks, jawab "Saya tidak menemukan informasi ini di dokumen."
3. Untuk pertanyaan yang membutuhkan perbandingan atau mencari nilai terbesar/terkecil (maksimum/minimum/terbanyak/tersedikit):
   - Baca SEMUA data yang tersedia di konteks dengan teliti.
   - Bandingkan SEMUA nilai yang relevan sebelum menentukan jawaban.
   - Cantumkan nilai dari SETIAP entri yang relevan agar perbandingan transparan.
   - Nyatakan jawaban akhir dengan jelas.
4. Untuk data tabular (tabel/spreadsheet):
   - Baca setiap baris secara sistematis sebelum menyimpulkan.
   - Anggap simbol strip ("-") atau nilai kosong sebagai nilai 0 atau tidak ada aktivitas.
5. Format jawaban: gunakan **bold** untuk nama/istilah penting, bullet list untuk enumerasi, paragraf biasa untuk penjelasan.

Konteks:
{context}

Pertanyaan: {question}

Jawaban:"""


def generate_answer(prompt: str) -> str:
    """Generate final answer from Gemini using the currently active generation model."""
    client = get_gemini_client()
    response = client.models.generate_content(
        model=get_generation_model(), contents=prompt
    )
    return response.text
