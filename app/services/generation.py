"""
Generation Agent — urus format prompt akhir & panggil Gemini API.
Sesuai AGENTS.md: logic generation HANYA di sini, tidak boleh bocor ke routes/.
"""

from app.core.config import GENERATION_MODEL, gemini_client


def build_prompt(question: str, chunks: list[str]) -> str:
    context = "\n\n".join(chunks)
    return f"""Jawab pertanyaan berikut HANYA berdasarkan konteks di bawah ini.
Kalau jawabannya tidak ada di konteks, katakan tidak tahu, jangan mengarang.

Konteks:
{context}

Pertanyaan: {question}

Jawaban:"""


def generate_answer(prompt: str) -> str:
    response = gemini_client.models.generate_content(
        model=GENERATION_MODEL, contents=prompt
    )
    return response.text
