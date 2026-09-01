import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from app.services.tabular_query import answer_tabular_question
from app.services.tabular.resolver import resolve_entities
from app.services.tabular.query_builder import build_query_plan, _resolve_operator_column, QueryBuildError
from app.services.tabular.classifier import classify_query, _get_operator_column

class TestTranshipmentQueries(unittest.TestCase):
    def setUp(self):
        self.category_name = "Transhipment"
        self.schema_mock = {
            "Transhipment ": ["VESSEL OPERATOR", "No", "SIZE", "YEAR", "DIRECT OR CY TRANS", "LOADING TERMINAL", "YARD REVENUE", "DISCHARGE TS", "Bulan", "20'", "40'", "MONTH"]
        }
        self.df_mock = pd.DataFrame([
            {"VESSEL OPERATOR": "MPN", "No": "C1", "SIZE": 20, "YEAR": 2024, "DIRECT OR CY TRANS": "Direct", "LOADING TERMINAL": "TTL", "20'": 1.0, "40'": 0.0, "_sheet": "Transhipment "},
            {"VESSEL OPERATOR": "SPI", "No": "C2", "SIZE": 40, "YEAR": 2024, "DIRECT OR CY TRANS": "CY", "LOADING TERMINAL": "TTL", "20'": 0.0, "40'": 1.0, "_sheet": "Transhipment "},
        ])

    def test_resolver_transhipment_operator_and_sizes(self):
        # Verify regional operators resolve correctly
        res1 = resolve_entities("Berapa total container 20’ milik operator MPN pada tahun 2024?", self.category_name)
        self.assertIn("MPN", res1.operators)
        self.assertIn("20'", res1.metrics)

        res2 = resolve_entities("Berapa total container 40’ milik operator TEMAS pada tahun 2024?", self.category_name)
        self.assertIn("TEMAS", res2.operators)
        self.assertIn("40'", res2.metrics)

        # Check various explicit aliases
        res3 = resolve_entities("Berapa container 20 feet SPI?", self.category_name)
        self.assertIn("20'", res3.metrics)
        self.assertIn("SPI", res3.operators)

        res4 = resolve_entities("Berapa container 40ft TIL?", self.category_name)
        self.assertIn("40'", res4.metrics)
        self.assertIn("TIL", res4.operators)

    def test_generic_container_fails_safely_when_no_metric(self):
        # When only generic "container" is used without size, we fail safely instead of guessing 20'
        res = resolve_entities("Operator mana yang memiliki container terbanyak pada tahun 2024?", self.category_name)
        self.assertNotIn("20'", res.metrics)
        self.assertNotIn("40'", res.metrics)

        # Build plan should throw QueryBuildError
        q_text = "Operator mana yang memiliki container terbanyak pada tahun 2024?"
        ast = classify_query(q_text, res, self.category_name)
        with self.assertRaises(QueryBuildError):
            build_query_plan(ast, q_text, res, self.category_name, self.schema_mock)

    def test_dataset_aware_operator_column_resolution(self):
        # Transhipment resolves to VESSEL OPERATOR
        col_trans = _get_operator_column("Transhipment")
        self.assertEqual(col_trans, "VESSEL OPERATOR")

        # Overview Vessel resolves to LOP
        col_vessel = _get_operator_column("Overview Vessel")
        self.assertEqual(col_vessel, "LOP")

        # Market Share resolves to LOP
        col_ms = _get_operator_column("Market Share")
        self.assertEqual(col_ms, "LOP")

    @patch("app.services.tabular_query.get_db_conn")
    @patch("app.services.tabular.executor.load_dataframe")
    def test_query_plan_and_execution_transhipment(self, mock_load, mock_db):
        mock_conn = mock_db.return_value.__enter__.return_value
        mock_conn.execute.return_value.fetchone.return_value = (1, self.schema_mock)
        mock_load.return_value = self.df_mock

        # Test Query 1: total 20' for MPN
        res = answer_tabular_question("Berapa total container 20’ milik operator MPN pada tahun 2024?", self.category_name)
        self.assertIn("1", res["answer"])
        self.assertIn("MPN", res["answer"])

        # Test Query 5: SPI with Direct status
        res = answer_tabular_question("Berapa container 20’ untuk SPI yang berstatus Direct pada tahun 2024?", self.category_name)
        self.assertIn("SPI", res["answer"])

        # Test Query 6: SPI with Loading Terminal TTL
        res = answer_tabular_question("Berapa container 20’ untuk SPI yang menggunakan Loading Terminal TTL pada tahun 2024?", self.category_name)
        self.assertIn("SPI", res["answer"])

    def test_ranking_semantics_quantity_and_rate(self):
        # 1. Transhipment 20' ranking uses SUM
        res_20 = resolve_entities("Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", "Transhipment")
        ast_20 = classify_query("Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", res_20, "Transhipment")
        self.assertEqual(ast_20.aggregation.func, "sum")
        self.assertEqual(ast_20.aggregation.column, "20'")
        
        plan_20 = build_query_plan(ast_20, "Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", res_20, "Transhipment", self.schema_mock)
        self.assertEqual(plan_20.aggregation.func, "sum")
        self.assertEqual(plan_20.aggregation.column, "20'")
        self.assertEqual(plan_20.group_by, ["VESSEL OPERATOR"])
        self.assertEqual(plan_20.sort, "desc")
        self.assertEqual(plan_20.limit, 1)

        # 2. Transhipment 40' ranking uses SUM
        res_40 = resolve_entities("Vessel operator mana yang memiliki container 40' terbanyak pada tahun 2024?", "Transhipment")
        ast_40 = classify_query("Vessel operator mana yang memiliki container 40' terbanyak pada tahun 2024?", res_40, "Transhipment")
        self.assertEqual(ast_40.aggregation.func, "sum")
        self.assertEqual(ast_40.aggregation.column, "40'")

        # 3. Overview Vessel TEUS ranking uses SUM
        ov_schema = {
            "DOMESTIC": ["YEAR", "MONTH", "LOP", "TEUS", "Boxes", "BCH", "BSH"]
        }
        res_teus = resolve_entities("Operator mana yang memiliki TEUS terbanyak pada tahun 2024?", "Overview Vessel")
        ast_teus = classify_query("Operator mana yang memiliki TEUS terbanyak pada tahun 2024?", res_teus, "Overview Vessel")
        self.assertEqual(ast_teus.aggregation.func, "sum")
        self.assertEqual(ast_teus.aggregation.column, "TEUS")
        
        plan_teus = build_query_plan(ast_teus, "Operator mana yang memiliki TEUS terbanyak pada tahun 2024?", res_teus, "Overview Vessel", ov_schema)
        self.assertEqual(plan_teus.group_by, ["LOP"])

        # 4. BCH ranking continues using MAX
        res_bch = resolve_entities("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Overview Vessel")
        ast_bch = classify_query("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_bch, "Overview Vessel")
        self.assertEqual(ast_bch.aggregation.func, "max")
        self.assertEqual(ast_bch.aggregation.column, "BCH")

        # 5. Percentage ranking continues using MAX
        ms_schema = {
            "V.OPR DOM": ["YEAR", "MONTH", "OPERATOR", "%"]
        }
        res_pct = resolve_entities("Operator mana yang memiliki market share tertinggi pada tahun 2024?", "Market Share")
        ast_pct = classify_query("Operator mana yang memiliki market share tertinggi pada tahun 2024?", res_pct, "Market Share")
        self.assertEqual(ast_pct.aggregation.func, "max")
        self.assertEqual(ast_pct.aggregation.column, "%")

    @patch("app.services.tabular_query.get_db_conn")
    @patch("app.services.tabular.executor.load_dataframe")
    def test_ranking_semantics_new_fixes(self, mock_load, mock_db):
        mock_conn = mock_db.return_value.__enter__.return_value
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        orig_cols = SCHEMA_REGISTRY["Transhipment"]["columns"]
        SCHEMA_REGISTRY["Transhipment"]["columns"] = orig_cols + ["BCH", "BSH"]

        try:
            # Test Case 1: BCH ranking uses MAX(BCH) and runs successfully without duplicate column error
            schema_bch = {
                "Transhipment ": ["VESSEL OPERATOR", "No", "SIZE", "YEAR", "DIRECT OR CY TRANS", "LOADING TERMINAL", "YARD REVENUE", "DISCHARGE TS", "Bulan", "20'", "40'", "MONTH", "BCH"]
            }
            df_bch = pd.DataFrame([
                {"VESSEL OPERATOR": "MPN", "No": "C1", "SIZE": 20, "YEAR": 2024, "20'": 1.0, "40'": 0.0, "BCH": 150.0, "_sheet": "Transhipment "},
                {"VESSEL OPERATOR": "SPI", "No": "C2", "SIZE": 40, "YEAR": 2024, "20'": 0.0, "40'": 1.0, "BCH": 200.0, "_sheet": "Transhipment "},
            ])
            mock_conn.execute.return_value.fetchone.return_value = (1, schema_bch)
            mock_load.return_value = df_bch

            res_bch = answer_tabular_question("Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Transhipment")
            self.assertIn("SPI", res_bch["answer"])
            self.assertIn("200", res_bch["answer"])

            # Test Case 2: BSH ranking uses MAX(BSH) and runs successfully without duplicate column error
            schema_bsh = {
                "Transhipment ": ["VESSEL OPERATOR", "No", "SIZE", "YEAR", "DIRECT OR CY TRANS", "LOADING TERMINAL", "YARD REVENUE", "DISCHARGE TS", "Bulan", "20'", "40'", "MONTH", "BSH"]
            }
            df_bsh = pd.DataFrame([
                {"VESSEL OPERATOR": "MPN", "No": "C1", "SIZE": 20, "YEAR": 2024, "20'": 1.0, "40'": 0.0, "BSH": 350.0, "_sheet": "Transhipment "},
                {"VESSEL OPERATOR": "SPI", "No": "C2", "SIZE": 40, "YEAR": 2024, "20'": 0.0, "40'": 1.0, "BSH": 300.0, "_sheet": "Transhipment "},
            ])
            mock_conn.execute.return_value.fetchone.return_value = (1, schema_bsh)
            mock_load.return_value = df_bsh

            res_bsh = answer_tabular_question("Vessel operator mana yang memiliki BSH tertinggi pada tahun 2024?", "Transhipment")
            self.assertIn("MPN", res_bsh["answer"])
            self.assertIn("350", res_bsh["answer"])

            # Test Case 3: TEUS bottom ranking uses SUM(TEUS), LOP group_by, ASC sort, LIMIT 1
            # and has 0 retry count (no retry strategy applied on ALL_ZERO or VALID)
            schema_ov = {
                "DOMESTIC": ["YEAR", "MONTH", "LOP", "TEUS", "Boxes", "BCH", "BSH"]
            }
            # SPI has 0.0 TEUS, MPN has 500.0 TEUS. Minimum is SPI (0.0).
            df_ov = pd.DataFrame([
                {"LOP": "SPI", "YEAR": 2024, "TEUS": 0.0, "_sheet": "DOMESTIC"},
                {"LOP": "MPN", "YEAR": 2024, "TEUS": 500.0, "_sheet": "DOMESTIC"},
            ])
            mock_conn.execute.return_value.fetchone.return_value = (1, schema_ov)
            mock_load.return_value = df_ov

            res_ov = answer_tabular_question("Operator mana yang memiliki TEUS paling sedikit pada tahun 2024?", "Overview Vessel")
            # Ensure it resolves correctly to SPI with sum(TEUS) returning 0.0
            self.assertIn("SPI", res_ov["answer"])
            # Verify no unnecessary count aggregation retry in the core answer
            core_ans = res_ov["answer"].split("\n\n---\n### Debug Information")[0]
            self.assertNotIn("Count", core_ans)

            # Test Case 4: Market share safe rejection if % column not available
            res_ms_fail = answer_tabular_question("Operator mana yang memiliki market share tertinggi pada tahun 2024?", "Overview Vessel")
            self.assertIn("Metric 'market share' tidak tersedia pada dataset 'Overview Vessel'", res_ms_fail["answer"])

            # Test Case 5: Market share passes if % column available
            schema_ms = {
                "V.OPR DOM": ["YEAR", "MONTH", "OPERATOR", "%"]
            }
            df_ms = pd.DataFrame([
                {"OPERATOR": "SPI", "YEAR": 2024, "%": 0.15, "_sheet": "V.OPR DOM"},
                {"OPERATOR": "MPN", "YEAR": 2024, "%": 0.25, "_sheet": "V.OPR DOM"},
            ])
            mock_conn.execute.return_value.fetchone.return_value = (1, schema_ms)
            mock_load.return_value = df_ms

            res_ms_pass = answer_tabular_question("Operator mana yang memiliki market share tertinggi pada tahun 2024?", "Market Share")
            self.assertIn("MPN", res_ms_pass["answer"])
        finally:
            SCHEMA_REGISTRY["Transhipment"]["columns"] = orig_cols

    def test_new_targeted_bug_fixes(self):
        from app.services.tabular.resolver import sanitize_leading_number, resolve_entities
        from app.services.tabular.domain_models import QueryType, UserIntent
        from app.services.tabular.query_builder import QueryBuildError, build_query_plan
        from app.services.tabular.classifier import classify_query
        # 1. Leading question number is removed before semantic parsing
        self.assertEqual(
            sanitize_leading_number("5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?"),
            "Bagaimana tren TEUS TIL per bulan pada tahun 2024?"
        )
        self.assertEqual(
            sanitize_leading_number("5. Bagaimana tren TEUS TIL per bulan pada tahun 2024?"),
            "Bagaimana tren TEUS TIL per bulan pada tahun 2024?"
        )
        self.assertEqual(
            sanitize_leading_number("5) Bagaimana tren TEUS TIL per bulan pada tahun 2024?"),
            "Bagaimana tren TEUS TIL per bulan pada tahun 2024?"
        )
        # Legitimate numbers are preserved
        self.assertEqual(
            sanitize_leading_number("20' untuk SPI tahun 2024"),
            "20' untuk SPI tahun 2024"
        )
        self.assertEqual(
            sanitize_leading_number("5 TEUS TIL"),
            "5 TEUS TIL"
        )

        # 2. "5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?" does not resolve month 5
        res_5 = resolve_entities("5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?", "Overview Vessel")
        self.assertEqual(res_5.month.month_str, "")
        self.assertEqual(res_5.month.month_code, 0)
        self.assertEqual(res_5.month.year, 2024)

        # 3. Trend TEUS TIL still uses: sum(TEUS) grouped by MONTH
        ast_trend = classify_query("5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?", res_5, "Overview Vessel")
        self.assertEqual(ast_trend.query_type, QueryType.TREND)
        self.assertEqual(ast_trend.intent, UserIntent.TREND_ANALYSIS)
        
        ov_schema = {
            "DOMESTIC": ["YEAR", "MONTH", "LOP", "TEUS", "Boxes", "BCH", "BSH"]
        }
        plan_trend = build_query_plan(ast_trend, "5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?", res_5, "Overview Vessel", ov_schema)
        self.assertEqual(plan_trend.aggregation.func, "sum")
        self.assertEqual(plan_trend.aggregation.column, "TEUS")
        self.assertEqual(plan_trend.group_by, ["MONTH"])

        # 4. BCH ranking on Transhipment is rejected because BCH does not exist
        res_bch_trans = resolve_entities("Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Transhipment")
        ast_bch_trans = classify_query("Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_bch_trans, "Transhipment")
        
        trans_schema = {
            "Transhipment": ["VESSEL OPERATOR", "No", "SIZE", "YEAR", "DIRECT OR CY TRANS", "LOADING TERMINAL", "YARD REVENUE", "DISCHARGE TS", "Bulan", "20'", "40'", "MONTH"]
        }
        with self.assertRaises(QueryBuildError) as ctx:
            build_query_plan(ast_bch_trans, "Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_bch_trans, "Transhipment", trans_schema)
        self.assertIn("Metric 'BCH' tidak tersedia pada dataset 'Transhipment'", str(ctx.exception))

        # 5. BCH ranking on Overview Vessel continues to work with: max(BCH) grouped by LOP
        res_bch_ov = resolve_entities("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Overview Vessel")
        ast_bch_ov = classify_query("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_bch_ov, "Overview Vessel")
        plan_bch_ov = build_query_plan(ast_bch_ov, "Operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_bch_ov, "Overview Vessel", ov_schema)
        self.assertEqual(plan_bch_ov.aggregation.func, "max")
        self.assertEqual(plan_bch_ov.aggregation.column, "BCH")
        self.assertEqual(plan_bch_ov.group_by, ["LOP"])

        # 6. Existing Transhipment 20' ranking continues to use: sum(20') grouped by VESSEL OPERATOR
        res_20_trans = resolve_entities("Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", "Transhipment")
        ast_20_trans = classify_query("Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", res_20_trans, "Transhipment")
        plan_20_trans = build_query_plan(ast_20_trans, "Vessel operator mana yang memiliki container 20' terbanyak pada tahun 2024?", res_20_trans, "Transhipment", trans_schema)
        self.assertEqual(plan_20_trans.aggregation.func, "sum")
        self.assertEqual(plan_20_trans.aggregation.column, "20'")
        self.assertEqual(plan_20_trans.group_by, ["VESSEL OPERATOR"])

        # 7. Existing Transhipment 40' ranking continues to use: sum(40') grouped by VESSEL OPERATOR
        res_40_trans = resolve_entities("Vessel operator mana yang memiliki container 40' terbanyak pada tahun 2024?", "Transhipment")
        ast_40_trans = classify_query("Vessel operator mana yang memiliki container 40' terbanyak pada tahun 2024?", res_40_trans, "Transhipment")
        plan_40_trans = build_query_plan(ast_40_trans, "Vessel operator mana yang memiliki container 40' terbanyak pada tahun 2024?", res_40_trans, "Transhipment", trans_schema)
        self.assertEqual(plan_40_trans.aggregation.func, "sum")
        self.assertEqual(plan_40_trans.aggregation.column, "40'")
        self.assertEqual(plan_40_trans.group_by, ["VESSEL OPERATOR"])

        # 8. Existing ambiguous "Berapa total container untuk SPI pada tahun 2024?" remains safely rejected
        res_ambig = resolve_entities("Berapa total container untuk SPI pada tahun 2024?", "Transhipment")
        ast_ambig = classify_query("Berapa total container untuk SPI pada tahun 2024?", res_ambig, "Transhipment")
        with self.assertRaises(QueryBuildError):
            build_query_plan(ast_ambig, "Berapa total container untuk SPI pada tahun 2024?", res_ambig, "Transhipment", trans_schema)

if __name__ == "__main__":
    unittest.main()
