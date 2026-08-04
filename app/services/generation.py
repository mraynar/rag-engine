from datetime import datetime, timezone, timedelta
from app.core.config import get_generation_model, get_gemini_client


def build_prompt(question: str, chunks: list[str]) -> str:
    # Get current time in WIB (UTC+7)
    wib_tz = timezone(timedelta(hours=7))
    now_wib = datetime.now(wib_tz)
    
    days = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
    months = [
        "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
        "Juli", "Agustus", "September", "Oktober", "November", "Desember"
    ]
    
    day_name = days[now_wib.weekday()]
    month_name = months[now_wib.month]
    formatted_date = f"{day_name}, {now_wib.day} {month_name} {now_wib.year}"

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
