"""
Unit tests for formatter.py - natural-language response generation.
TDD: Tests written BEFORE implementation.
"""
import unittest
import pandas as pd

from app.services.tabular.domain_models import (
    QueryAST,
    QueryPlan,
    QueryType,
    UserIntent,
    BuildMethod,
    ExecutionResult,
    ResultQuality,
    ResolvedEntities,
    MonthContext,
    RetryStrategy,
    AggregationSpec,
)


class TestFormatterBasic(unittest.TestCase):
    """Test basic formatting, decimals, integers, and thousand separators."""

    def test_simple_scalar_result(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities(operators=["TIL"], metrics=["BCH"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=123.45, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Berapa BCH TIL?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )

        self.assertIn("BCH", res)
        self.assertIn("TIL", res)
        self.assertIn("123,45", res)

    def test_integer_formatting(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=1000.0, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Berapa total TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("1.000", res)
        self.assertNotIn("1000,0", res)

    def test_decimal_formatting(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities(metrics=["BCH"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=1234.567, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Berapa BCH?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("1.234,57", res)  # Rounded to 2 decimals

    def test_indonesian_thousand_separator(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=1234567, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Berapa total TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("1.234.567", res)


class TestFormatterAggregation(unittest.TestCase):
    """Test aggregation formatting for SUM, COUNT, and MAX/MIN."""

    def test_sum_result(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=500000, quality=ResultQuality.VALID, row_count=10)
        }

        res = format_response(
            question="Berapa total TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("total", res.lower())
        self.assertIn("500.000", res)

    def test_count_result(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities(metrics=["vessel"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("count"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=25, quality=ResultQuality.VALID, row_count=25)
        }

        res = format_response(
            question="Berapa jumlah transaksi?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Transhipment",
            original_plan=plan
        )
        self.assertIn("jumlah", res.lower())
        self.assertIn("25", res)
        self.assertNotIn("total sum", res.lower())

    def test_max_min_result(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("max", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=8000, quality=ResultQuality.VALID, row_count=10)
        }

        res = format_response(
            question="Berapa TEUS tertinggi?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("tertinggi", res.lower())
        self.assertIn("8.000", res)


class TestFormatterRanking(unittest.TestCase):
    """Test TOP_N and BOTTOM_N ranking queries."""

    def test_ranking_top_n(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.RANKING, UserIntent.TOP_N)
        resolved = ResolvedEntities(metrics=["BCH"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "BCH"), ["LOP"], "desc", 1, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([{"LOP": "TIL", "BCH": 123.45}])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Operator mana yang memiliki BCH tertinggi?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("tertinggi", res)
        self.assertIn("TIL", res)
        self.assertIn("123,45", res)

    def test_ranking_bottom_n(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.RANKING, UserIntent.BOTTOM_N)
        resolved = ResolvedEntities(metrics=["BCH"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "BCH"), ["LOP"], "asc", 1, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([{"LOP": "SPI", "BCH": 50.2}])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Operator mana yang memiliki BCH terendah?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("terendah", res)
        self.assertIn("SPI", res)
        self.assertIn("50,2", res)


class TestFormatterTrend(unittest.TestCase):
    """Test trend analysis formatting."""

    def test_trend_monthly(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.TREND, UserIntent.TREND_ANALYSIS)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), ["MONTH"], None, None, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([
            {"MONTH": "Januari", "TEUS": 1000.0},
            {"MONTH": "Februari", "TEUS": 1200.0},
        ])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Bagaimana tren TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("Januari: 1.000", res)
        self.assertIn("Februari: 1.200", res)

    def test_trend_yearly(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.TREND, UserIntent.TREND_ANALYSIS)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), ["YEAR"], None, None, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([
            {"YEAR": 2023, "TEUS": 10000.0},
            {"YEAR": 2024, "TEUS": 15000.0},
        ])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Bagaimana tren TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("2023: 10.000", res)
        self.assertIn("2024: 15.000", res)


class TestFormatterComparison(unittest.TestCase):
    """Test comparison and multi-hop query formatting."""

    def test_single_query_comparison(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.COMPARISON, UserIntent.COMPARISON)
        resolved = ResolvedEntities(metrics=["TEUS"], operators=["TIL", "SPI"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), ["LOP"], None, None, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([
            {"LOP": "TIL", "TEUS": 1000.0},
            {"LOP": "SPI", "TEUS": 800.0},
        ])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Bandingkan TEUS TIL dan SPI",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("TIL", res)
        self.assertIn("1.000", res)
        self.assertIn("SPI", res)
        self.assertIn("800", res)

    def test_multihop_year_difference(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.MULTI_HOP, UserIntent.MULTI_HOP)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=100000.0, quality=ResultQuality.VALID, row_count=1),  # 2024
            2: ExecutionResult(data=120000.0, quality=ResultQuality.VALID, row_count=1),  # 2025
        }

        res = format_response(
            question="Berapa selisih TEUS tahun 2024 dan 2025?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("selisih", res.lower())
        self.assertIn("20.000", res)

    def test_multihop_month_difference(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.MULTI_HOP, UserIntent.MULTI_HOP)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=1000.0, quality=ResultQuality.VALID, row_count=1),
            2: ExecutionResult(data=1500.0, quality=ResultQuality.VALID, row_count=1),
        }

        res = format_response(
            question="Berapa beda TEUS Januari dan Februari?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("500", res)

    def test_bandingkan_without_difference(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.COMPARISON, UserIntent.COMPARISON)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan(None, [], AggregationSpec("sum", "TEUS"), ["_sheet"], None, None, BuildMethod.DETERMINISTIC)

        df = pd.DataFrame([
            {"_sheet": "DOMESTIC", "TEUS": 1000.0},
            {"_sheet": "INTERNATIONAL", "TEUS": 8000.0},
        ])
        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Bandingkan TEUS domestic dan international",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("DOMESTIC: 1.000", res)
        self.assertIn("INTERNATIONAL: 8.000", res)
        self.assertNotIn("selisih", res.lower())


class TestFormatterPercentage(unittest.TestCase):
    """Test percentage query formatting."""

    def test_percentage_lookup(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.PERCENTAGE_LOOKUP)
        resolved = ResolvedEntities(operators=["TIL"], metrics=["market share"])
        plan = QueryPlan("V.OPR DOM", [], AggregationSpec("sum", "%"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=23.5, quality=ResultQuality.VALID, row_count=1)
        }

        res = format_response(
            question="Berapa market share TIL?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Market Share",
            original_plan=plan
        )
        self.assertIn("23,5%", res)


class TestFormatterQuality(unittest.TestCase):
    """Test response formatting for non-VALID ResultQuality values."""

    def test_quality_empty(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=None, quality=ResultQuality.EMPTY, row_count=0)
        }

        res = format_response(
            question="Berapa TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("tidak ditemukan", res.lower())

    def test_quality_nan(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=None, quality=ResultQuality.NAN, row_count=10)
        }

        res = format_response(
            question="Berapa total TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("tidak dapat dihitung", res.lower())

    def test_quality_all_zero(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], AggregationSpec("sum", "TEUS"), None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=0.0, quality=ResultQuality.ALL_ZERO, row_count=5)
        }

        res = format_response(
            question="Berapa total TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("nilainya adalah 0", res.lower())


class TestFormatterDataStructures(unittest.TestCase):
    """Test formatting raw Series and other fallback formats safely."""

    def test_series_result(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        series = pd.Series([100, 200], index=["TIL", "SPI"])
        results = {
            1: ExecutionResult(data=series, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Berapa data LOP?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("TIL: 100", res)
        self.assertIn("SPI: 200", res)


class TestFormatterSafety(unittest.TestCase):
    """Test safety, retry audits, and error mitigation conventions."""

    def test_missing_multihop_result(self):
        """Should return gracefully if multi-hop results are incomplete."""
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.MULTI_HOP, UserIntent.MULTI_HOP)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(data=100.0, quality=ResultQuality.VALID, row_count=1)
            # Step 2 is missing!
        }

        res = format_response(
            question="Berapa selisih TEUS 2024 dan 2025?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        # Should not crash, and should report the step 1 result safely
        self.assertIn("100", res)

    def test_retry_metadata_no_leak(self):
        """Should not leak strategy names like 'MONTH_RETRY' to users."""
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(
                data=123.0,
                quality=ResultQuality.VALID,
                row_count=1,
                retry_count=1,
                last_retry_strategy=RetryStrategy.MONTH_RETRY
            )
        }

        res = format_response(
            question="Berapa TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertNotIn("MONTH_RETRY", res)
        self.assertNotIn("retry_strategy", res.lower())

    def test_sheet_retry_no_provenance_invention(self):
        """Should not fabricate sheet change logs unless full provenance is exposed."""
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities()
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        results = {
            1: ExecutionResult(
                data=123.0,
                quality=ResultQuality.VALID,
                row_count=1,
                retry_count=1,
                last_retry_strategy=RetryStrategy.SHEET_RETRY
            )
        }

        res = format_response(
            question="Berapa TEUS?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        # Should format naturally and not invent sheet swap descriptions
        self.assertIn("123", res)
        self.assertNotIn("DOMESTIC menjadi INTERNATIONAL", res)


class TestFormatterRegression(unittest.TestCase):
    def test_value_lookup_dataframe_coercion_sum(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities(metrics=["TEUS"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        # DataFrame containing numeric values as strings (object dtype)
        df = pd.DataFrame([
            {"TEUS": "4012"},
            {"TEUS": "4380"},
            {"TEUS": "5601"},
        ])

        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=3)
        }

        res = format_response(
            question="Berapa TEUS TIL tahun 2024?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("13.993", res)
        self.assertNotIn("40124380", res)

    def test_value_lookup_dataframe_coercion_mean(self):
        from app.services.tabular.formatter import format_response

        ast = QueryAST(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        resolved = ResolvedEntities(metrics=["BCH"])
        plan = QueryPlan("DOMESTIC", [], None, None, None, None, BuildMethod.DETERMINISTIC)

        # BCH is a rate, should calculate mean (average)
        df = pd.DataFrame([
            {"BCH": "20"},
            {"BCH": "30"},
        ])

        results = {
            1: ExecutionResult(data=df, quality=ResultQuality.VALID, row_count=2)
        }

        res = format_response(
            question="Berapa BCH TIL tahun 2024?",
            results=results,
            ast=ast,
            resolved=resolved,
            dataset="Overview Vessel",
            original_plan=plan
        )
        self.assertIn("25", res)


if __name__ == "__main__":
    unittest.main()
