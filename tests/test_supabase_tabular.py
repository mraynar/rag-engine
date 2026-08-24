import json
import unittest
from unittest.mock import MagicMock, patch

import pandas as pd
from sqlalchemy import text

from app.services.db import get_db_conn
from app.services.tabular_ingestion import sync_tabular_source
from app.services.tabular_query import answer_tabular_question


class TestSupabaseTabular(unittest.TestCase):
    def setUp(self):
        self.category_name = "Test Tabular Category"
        self.source_url = "https://example.com/test_data.xlsx"
        self.source_type = "sharepoint"

    def tearDown(self):
        # Clean up database test entries
        try:
            with get_db_conn() as conn:
                with conn.begin():
                    conn.execute(
                        text("DELETE FROM data_sources WHERE category_name = :cat"),
                        {"cat": self.category_name}
                    )
        except Exception:
            pass

    @patch("app.services.tabular_ingestion.download_sharepoint_file")
    @patch("app.services.tabular_ingestion.download_googledrive_file")
    @patch("pandas.read_excel")
    def test_sync_tabular_source_lifecycle(self, mock_read_excel, mock_download_gdrive, mock_download_sharepoint):
        # Setup mock fetcher downloads
        mock_download_sharepoint.return_value = "fallback_download"
        mock_download_gdrive.return_value = "google_sheets_download"

        # Mock Excel parser dataframes
        df_sheet1 = pd.DataFrame({
            "Date": ["2023-01-01", "2023-01-02"],
            "LOP": ["TIL", "SPI"],
            "TEUS": [4170, 5200]
        })
        mock_read_excel.return_value = {"Sheet1": df_sheet1}

        # Run tabular sync
        result = sync_tabular_source(self.category_name, self.source_url, self.source_type)

        self.assertEqual(result["category_name"], self.category_name)
        self.assertEqual(result["sync_status"], "success")
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(result["fetch_method"], "fallback_download")

        # Verify schema is populated
        schema = result["column_schema"]
        if isinstance(schema, str):
            schema = json.loads(schema)
        self.assertIn("Sheet1", schema)
        self.assertEqual(schema["Sheet1"], ["Date", "LOP", "TEUS"])

    @patch("app.services.tabular_query.get_gemini_client")
    def test_answer_tabular_question_with_pandas_filtering(self, mock_get_client):
        # 1. Manually insert test records to DB first
        with get_db_conn() as conn:
            with conn.begin():
                # Clean up first
                conn.execute(
                    text("DELETE FROM data_sources WHERE category_name = :cat"),
                    {"cat": self.category_name}
                )
                # Insert source
                source_id = conn.execute(
                    text("""
                        INSERT INTO data_sources (category_name, source_url, source_type, sync_status, column_schema)
                        VALUES (:cat, :url, :type, 'success', :schema)
                        RETURNING id
                    """),
                    {
                        "cat": self.category_name,
                        "url": self.source_url,
                        "type": self.source_type,
                        "schema": json.dumps({"Sheet1": ["Date", "LOP", "TEUS"]})
                    }
                ).fetchone()[0]

                # Insert data rows
                insert_row = text("""
                    INSERT INTO data_rows (source_id, sheet_name, row_index, row_data)
                    VALUES (:source_id, :sheet, :idx, :data)
                """)
                conn.execute(insert_row, [
                    {
                        "source_id": source_id,
                        "sheet": "Sheet1",
                        "idx": 0,
                        "data": json.dumps({"Date": "2023-01-01", "LOP": "TIL", "TEUS": 4170})
                    },
                    {
                        "source_id": source_id,
                        "sheet": "Sheet1",
                        "idx": 1,
                        "data": json.dumps({"Date": "2023-01-02", "LOP": "SPI", "TEUS": 5200})
                    }
                ])

        # 2. Mock Gemini API client & models
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock Call 1 response (Gemini translating to JSON parameters)
        mock_response_p1 = MagicMock()
        mock_response_p1.text = json.dumps({
            "sheet": "Sheet1",
            "filters": [
                {"column": "LOP", "operator": "==", "value": "TIL"}
            ],
            "aggregation": {
                "func": "sum",
                "column": "TEUS"
            },
            "group_by": None
        })

        # Mock Call 2 response (Gemini formulating final response)
        mock_response_p2 = MagicMock()
        mock_response_p2.text = "Berdasarkan data dari Test Tabular Category, LOP TIL memiliki total TEUS sebesar 4170."

        # Assign generate_content side_effects
        mock_client.models.generate_content.side_effect = [mock_response_p1, mock_response_p2]

        # Call query answer pipeline
        output = answer_tabular_question("Berapa TEUS TIL?", self.category_name)

        # Assert correct formatting and values
        self.assertTrue(any(v in output["answer"] for v in ["4170", "4.170"]))
        self.assertIn("Test Tabular Category", output["sources"][0])


if __name__ == "__main__":
    unittest.main()
