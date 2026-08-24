import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.services.tabular_query import answer_tabular_question

class TestObservabilityDebug(unittest.TestCase):
    def setUp(self):
        self.category_name = "Overview Vessel"
        self.question_single = "Berapa TEUS TIL tahun 2024?"
        self.question_multi = "Berapa selisih TEUS TIL tahun 2024 dan 2025?"
        self.schema_mock = {
            "sheets": ["DOMESTIC", "INTERNATIONAL"],
            "columns": ["YEAR", "MONTH", "LOP", "TEUS", "Boxes", "BCH", "BSH"]
        }
        self.df_mock = pd.DataFrame([
            {"YEAR": 2024, "MONTH": "Januari", "LOP": "TIL", "TEUS": 1000.0, "_sheet": "DOMESTIC"},
            {"YEAR": 2024, "MONTH": "Februari", "LOP": "TIL", "TEUS": 2000.0, "_sheet": "DOMESTIC"},
        ])

    @patch("app.services.tabular_query.get_db_conn")
    @patch("app.services.tabular.executor.load_dataframe")
    @patch("app.services.tabular_query.RETURN_DEBUG_BLOCK", False)
    def test_debug_block_absent_when_false(self, mock_load, mock_db):
        mock_conn = mock_db.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.return_value = (1, self.schema_mock)
        mock_load.return_value = self.df_mock

        res = answer_tabular_question(self.question_single, self.category_name)
        self.assertNotIn("Debug Information", res["answer"])
        self.assertNotIn("AST — Step 1", res["answer"])

    @patch("app.services.tabular_query.get_db_conn")
    @patch("app.services.tabular.executor.load_dataframe")
    @patch("app.services.tabular_query.RETURN_DEBUG_BLOCK", True)
    def test_debug_block_present_single_step(self, mock_load, mock_db):
        mock_conn = mock_db.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.return_value = (1, self.schema_mock)
        mock_load.return_value = self.df_mock

        res = answer_tabular_question(self.question_single, self.category_name)
        answer = res["answer"]
        self.assertIn("Debug Information", answer)
        self.assertIn("**Input**", answer)
        self.assertIn("Question: `Berapa TEUS TIL tahun 2024?`", answer)
        self.assertIn("Category: `Overview Vessel`", answer)
        self.assertIn("**Dataset Routing**", answer)
        self.assertIn("Dataset: `Overview Vessel`", answer)
        self.assertIn("**Sheet Routing**", answer)
        self.assertIn("**Entities**", answer)
        self.assertIn("Year: `2024`", answer)
        self.assertIn("**Classification**", answer)
        self.assertIn("Query Type: `simple`", answer)
        self.assertIn("**AST — Step 1**", answer)
        self.assertIn("**Query Plan — Step 1**", answer)
        self.assertIn("**Execution Result — Step 1**", answer)
        self.assertIn("Data Type: `DataFrame`", answer)
        self.assertIn("Shape: `(2, 5)`", answer)
        self.assertIn("Columns: `['YEAR', 'MONTH', 'LOP', 'TEUS', '_sheet']`", answer)

        # No credential exposure
        self.assertNotIn("api_key", answer.lower())
        self.assertNotIn("password", answer.lower())
        self.assertNotIn("secret", answer.lower())

    @patch("app.services.tabular_query.get_db_conn")
    @patch("app.services.tabular.executor.load_dataframe")
    @patch("app.services.tabular_query.RETURN_DEBUG_BLOCK", True)
    def test_debug_block_multi_hop(self, mock_load, mock_db):
        mock_conn = mock_db.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.return_value = (1, self.schema_mock)
        mock_load.return_value = self.df_mock

        res = answer_tabular_question(self.question_multi, self.category_name)
        answer = res["answer"]
        self.assertIn("Debug Information", answer)
        self.assertIn("AST — Step 1", answer)
        self.assertIn("AST — Step 2", answer)
        self.assertIn("Query Plan — Step 1", answer)
        self.assertIn("Query Plan — Step 2", answer)

        # No credential exposure
        self.assertNotIn("api_key", answer.lower())
        self.assertNotIn("password", answer.lower())
        self.assertNotIn("secret", answer.lower())
