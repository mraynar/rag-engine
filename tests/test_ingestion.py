import unittest
import pandas as pd
from app.services.ingestion import (
    _split_sentences,
    chunk_by_sentences,
    _dataframe_to_chunks,
)


class TestIngestion(unittest.TestCase):
    def test_split_sentences(self):
        text = "Halo dunia! Ini adalah kalimat kedua. Dan ini yang ketiga?"
        sentences = _split_sentences(text)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "Halo dunia!")
        self.assertEqual(sentences[1], "Ini adalah kalimat kedua.")
        self.assertEqual(sentences[2], "Dan ini yang ketiga?")

    def test_chunk_by_sentences_within_limit(self):
        text = "Kalimat pertama. Kalimat kedua yang agak panjang. Kalimat ketiga."
        chunks = chunk_by_sentences(text, chunk_size=300)
        self.assertEqual(len(chunks), 1)
        self.assertIn("Kalimat pertama.", chunks[0])
        self.assertIn("Kalimat ketiga.", chunks[0])

    def test_chunk_by_sentences_oversized(self):
        long_sentence = "A" * 350
        text = f"Pendek. {long_sentence}. Akhir."
        chunks = chunk_by_sentences(text, chunk_size=300)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[0], "Pendek.")
        self.assertEqual(chunks[1], f"{long_sentence}.")
        self.assertEqual(chunks[2], "Akhir.")

    def test_dataframe_to_chunks(self):
        data = {
            "Date": ["2023-01-01", "2023-02-01"],
            "LOP": ["TIL", "SPI"],
            "TEUS": [4170, 5200],
            "Notes": [None, "Normal"],
        }
        df = pd.DataFrame(data)
        chunks = _dataframe_to_chunks(df)

        self.assertEqual(len(chunks), 2)
        self.assertIn("Date: 2023-01-01", chunks[0])
        self.assertIn("LOP: TIL", chunks[0])
        self.assertIn("TEUS: 4170", chunks[0])
        self.assertNotIn("Notes", chunks[0])  # None value should be skipped
        self.assertIn("Notes: Normal", chunks[1])


if __name__ == "__main__":
    unittest.main()
