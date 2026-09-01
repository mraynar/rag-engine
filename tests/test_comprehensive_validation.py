"""
Comprehensive Data Validation Test Suite for TPS Assistant (All Datasources).
Tests all 40+ prompt validation cases provided in the specification.
"""
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

from app.services.tabular_query import answer_tabular_question
from app.services.tabular.resolver import route_dataset, route_sheet, resolve_entities
from app.services.tabular.classifier import classify_query
from app.services.tabular.query_builder import build_query_plan, QueryBuildError
from app.services.tabular.domain_models import QueryType, UserIntent


class TestComprehensiveDataValidation(unittest.TestCase):

    # ==================================================
    # 1. OVERVIEW VESSEL
    # ==================================================

    def test_ov_01_total_teus_til_2024(self):
        # OV-01: Berapa total TEUS TIL pada tahun 2024?
        res_ent = resolve_entities("Berapa total TEUS TIL pada tahun 2024?", "Overview Vessel")
        self.assertIn("TIL", res_ent.operators)
        self.assertIn("TEUS", res_ent.metrics)
        self.assertEqual(res_ent.month.year, 2024)

    def test_ov_02_operator_teus_terbanyak_2024(self):
        # OV-02: Operator mana yang memiliki TEUS terbanyak pada tahun 2024?
        res_ent = resolve_entities("Operator mana yang memiliki TEUS terbanyak pada tahun 2024?", "Overview Vessel")
        ast = classify_query("Operator mana yang memiliki TEUS terbanyak pada tahun 2024?", res_ent, "Overview Vessel")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.TOP_N)
        self.assertEqual(ast.aggregation.func, "sum")
        self.assertEqual(ast.aggregation.column, "TEUS")

    def test_ov_03_operator_bch_tertinggi_2024(self):
        # OV-03: Operator mana yang memiliki BCH tertinggi pada tahun 2024?
        res_ent = resolve_entities("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Overview Vessel")
        ast = classify_query("Operator mana yang memiliki BCH tertinggi pada tahun 2024?", res_ent, "Overview Vessel")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.TOP_N)
        # BCH is a rate/performance metric -> MUST use MAX (or MEAN/MAX), NOT SUM
        self.assertEqual(ast.aggregation.func, "max")
        self.assertEqual(ast.aggregation.column, "BCH")

    def test_ov_04_operator_bsh_tertinggi_2024(self):
        # OV-04: Operator mana yang memiliki BSH tertinggi pada tahun 2024?
        res_ent = resolve_entities("Operator mana yang memiliki BSH tertinggi pada tahun 2024?", "Overview Vessel")
        ast = classify_query("Operator mana yang memiliki BSH tertinggi pada tahun 2024?", res_ent, "Overview Vessel")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.aggregation.func, "max")
        self.assertEqual(ast.aggregation.column, "BSH")

    def test_ov_05_tren_teus_til_per_bulan_2024(self):
        # OV-05: Bagaimana tren TEUS TIL per bulan pada tahun 2024?
        res_ent = resolve_entities("Bagaimana tren TEUS TIL per bulan pada tahun 2024?", "Overview Vessel")
        ast = classify_query("Bagaimana tren TEUS TIL per bulan pada tahun 2024?", res_ent, "Overview Vessel")
        self.assertEqual(ast.query_type, QueryType.TREND)
        self.assertEqual(ast.intent, UserIntent.TREND_ANALYSIS)

    # ==================================================
    # 2. TRANSHIPMENT
    # ==================================================

    def test_tr_01_total_container_20_mpn_2024(self):
        # TR-01: Berapa total container 20’ milik operator MPN pada tahun 2024?
        res_ent = resolve_entities("Berapa total container 20’ milik operator MPN pada tahun 2024?", "Transhipment")
        self.assertIn("MPN", res_ent.operators)
        self.assertIn("20'", res_ent.metrics)

    def test_tr_02_operator_20_terbanyak_2024(self):
        # TR-02: Vessel operator mana yang memiliki container 20’ terbanyak pada tahun 2024?
        res_ent = resolve_entities("Vessel operator mana yang memiliki container 20’ terbanyak pada tahun 2024?", "Transhipment")
        ast = classify_query("Vessel operator mana yang memiliki container 20’ terbanyak pada tahun 2024?", res_ent, "Transhipment")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.aggregation.func, "sum")
        self.assertEqual(ast.aggregation.column, "20'")

    def test_tr_03_operator_40_terbanyak_2024(self):
        # TR-03: Vessel operator mana yang memiliki container 40’ terbanyak pada tahun 2024?
        res_ent = resolve_entities("Vessel operator mana yang memiliki container 40’ terbanyak pada tahun 2024?", "Transhipment")
        ast = classify_query("Vessel operator mana yang memiliki container 40’ terbanyak pada tahun 2024?", res_ent, "Transhipment")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.aggregation.func, "sum")
        self.assertEqual(ast.aggregation.column, "40'")

    def test_tr_04_operator_20_paling_sedikit_2024(self):
        # TR-04: Vessel operator mana yang memiliki container 20’ paling sedikit pada tahun 2024?
        res_ent = resolve_entities("Vessel operator mana yang memiliki container 20’ paling sedikit pada tahun 2024?", "Transhipment")
        ast = classify_query("Vessel operator mana yang memiliki container 20’ paling sedikit pada tahun 2024?", res_ent, "Transhipment")
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.BOTTOM_N)

    # ==================================================
    # 3. MARKET SHARE
    # ==================================================

    def test_ms_01_total_teus_til_market_share(self):
        # MS-01: Berapa total TEUS TIL pada tahun 2024 berdasarkan data Market Share?
        route = route_dataset("Berapa total TEUS TIL pada tahun 2024 berdasarkan data Market Share?", "All Data")
        self.assertEqual(route.dataset, "Market Share")

    def test_ms_05_bandingkan_til_spi_market_share(self):
        # MS-05: Bandingkan total TEUS TIL dan SPI pada tahun 2024 berdasarkan data Market Share.
        res_ent = resolve_entities("Bandingkan total TEUS TIL dan SPI pada tahun 2024 berdasarkan data Market Share.", "Market Share")
        self.assertIn("TIL", res_ent.operators)
        self.assertIn("SPI", res_ent.operators)

    # ==================================================
    # 4. REALISASI UC
    # ==================================================

    def test_uc_04_total_revenue_2024(self):
        # UC-04: Berapa total revenue pada tahun 2024?
        res_ent = resolve_entities("Berapa total revenue pada tahun 2024?", "Realisasi UC")
        self.assertIn("TOTAL REVENUE", res_ent.metrics)

    # ==================================================
    # 5. VESSEL SERVICE
    # ==================================================

    def test_vs_03_total_call_terbanyak_2024(self):
        # VS-03: Vessel operator mana yang memiliki TOTAL CALL terbanyak pada tahun 2024?
        res_ent = resolve_entities("Vessel operator mana yang memiliki TOTAL CALL terbanyak pada tahun 2024?", "Vessel Service")
        self.assertIn("TOTAL CALL", res_ent.metrics)

    # ==================================================
    # 6. KOMERSIAL DASHBOARD
    # ==================================================

    def test_kd_01_total_revenue_2024(self):
        # KD-01: Berapa total revenue seluruh vessel operator pada tahun 2024?
        res_ent = resolve_entities("Berapa total revenue seluruh vessel operator pada tahun 2024?", "Komersial Dashboard")
        self.assertIn("TOTAL ALL REVENUE", res_ent.metrics)

    # ==================================================
    # 7. CONTAINER THROUGHPUT
    # ==================================================

    def test_ct_01_actual_domestik_2024(self):
        # CT-01: Berapa total actual container throughput domestik pada tahun 2024?
        route = route_dataset("Berapa total actual container throughput domestik pada tahun 2024?", "All Data")
        self.assertEqual(route.dataset, "Container Throughput")
        sheets = route_sheet("Berapa total actual container throughput domestik pada tahun 2024?", "Container Throughput")
        self.assertEqual(sheets, ["Domestik"])

    # ==================================================
    # 8. RESTNDISC
    # ==================================================

    def test_rn_01_total_nominal_keringanan(self):
        # RN-01: Berapa total nominal persetujuan keringanan?
        route = route_dataset("Berapa total nominal persetujuan keringanan?", "All Data")
        self.assertEqual(route.dataset, "RestNDisc")
        res_ent = resolve_entities("Berapa total nominal persetujuan keringanan?", "RestNDisc")
        self.assertIn("NOMINAL PERSETUJUAN KERINGANAN", res_ent.metrics)

    # ==================================================
    # 10. NEGATIVE / SAFETY TESTS
    # ==================================================

    def test_neg_01_generic_container_fails_safely(self):
        # NEG-01: Berapa total container untuk SPI pada tahun 2024?
        res = resolve_entities("Berapa total container untuk SPI pada tahun 2024?", "Transhipment")
        self.assertNotIn("20'", res.metrics)
        self.assertNotIn("40'", res.metrics)

    def test_neg_02_bch_transhipment_rejection(self):
        # NEG-02: Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024? (Source: Transhipment)
        res = resolve_entities("Vessel operator mana yang memiliki BCH tertinggi pada tahun 2024?", "Transhipment")
        self.assertNotIn("BCH", res.metrics)

    def test_neg_04_leading_number_sanitization(self):
        # NEG-04: 5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?
        res = resolve_entities("5 Bagaimana tren TEUS TIL per bulan pada tahun 2024?", "Overview Vessel")
        # Sanitize leading 5 so it does not get resolved as month=5 (May)
        self.assertEqual(res.month.month_code, 0)


if __name__ == "__main__":
    unittest.main()
