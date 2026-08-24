import unittest
from app.services.tabular_query import answer_tabular_question

class TestTabularBenchmark(unittest.TestCase):

    def test_vessel_teus_2025(self):
        res = answer_tabular_question("Berapa total TEUS tahun 2025?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("8.561.595", answer)

    def test_vessel_teus_2024(self):
        res = answer_tabular_question("Berapa total TEUS tahun 2024?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("3.016.969", answer)

    def test_vessel_transaksi_2024(self):
        res = answer_tabular_question("Berapa total transaksi tahun 2024?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("3.016.969", answer)

    def test_vessel_boxes_2025(self):
        res = answer_tabular_question("Berapa total box tahun 2025?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("8.561.595", answer)

    def test_vessel_selisih_teus(self):
        res = answer_tabular_question("Berapa selisih TEUS tahun 2024 dan 2025?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("5.544.626", answer)

    def test_vessel_aktivitas_tertinggi(self):
        res = answer_tabular_question("Tahun berapa aktivitas tertinggi?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("2024", answer)
        self.assertIn("288.469", answer)

    def test_vessel_persentase_internasional_2025(self):
        res = answer_tabular_question("Berapa persentase kontribusi TEUS internasional pada tahun 2025?", "Overview Vessel")
        answer = res["answer"]
        self.assertIn("95,53%", answer)

    def test_transhipment_transaksi_2024(self):
        res = answer_tabular_question("Berapa total transaksi tahun 2024?", "Transhipment")
        answer = res["answer"]
        self.assertIn("3.624", answer)

    def test_deleted_category_warning(self):
        res = answer_tabular_question("Berapa total transaksi?", "Non Existent Category")
        answer = res["answer"]
        self.assertIn("tidak ditemukan di database", answer)

if __name__ == "__main__":
    unittest.main()
