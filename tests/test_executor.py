"""
Unit tests for executor.py - pandas data loading, filtering, aggregation, and quality checks.
TDD: Tests written BEFORE implementation.
"""
import json
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from app.services.tabular.domain_models import (
    QueryPlan,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    BuildMethod,
    ExecutionResult,
    ResultQuality,
)


class TestExecutorDataLoading(unittest.TestCase):
    """Test database loading and DataFrame construction."""

    @patch("app.services.tabular.executor.get_db_conn")
    def test_load_dataframe_all_sheets(self, mock_get_db_conn):
        """Should load rows from all sheets when plan.sheet is None."""
        from app.services.tabular.executor import load_dataframe

        # Mock connection and cursor/execute
        mock_conn = MagicMock()
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn

        # Mock query result
        mock_conn.execute.return_value.fetchall.return_value = [
            ("DOMESTIC", {"YEAR": 2024, "LOP": "TIL", "TEUS": 100}),
            ("INTERNATIONAL", {"YEAR": 2024, "LOP": "SPI", "TEUS": 200}),
        ]

        df = load_dataframe(source_id="dummy-uuid", sheet=None)

        self.assertEqual(len(df), 2)
        self.assertIn("_sheet", df.columns)
        self.assertEqual(df.loc[0, "_sheet"], "DOMESTIC")
        self.assertEqual(df.loc[1, "_sheet"], "INTERNATIONAL")
        self.assertEqual(df.loc[0, "TEUS"], 100)

    @patch("app.services.tabular.executor.get_db_conn")
    def test_load_dataframe_single_sheet(self, mock_get_db_conn):
        """Should query with sheet filter when plan.sheet is provided."""
        from app.services.tabular.executor import load_dataframe

        mock_conn = MagicMock()
        mock_get_db_conn.return_value.__enter__.return_value = mock_conn
        mock_conn.execute.return_value.fetchall.return_value = [
            ("DOMESTIC", {"YEAR": 2024, "LOP": "TIL", "TEUS": 100})
        ]

        df = load_dataframe(source_id="dummy-uuid", sheet="DOMESTIC")

        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "_sheet"], "DOMESTIC")
        # Verify execute SQL parameters contain lowercased sheet
        args, kwargs = mock_conn.execute.call_args
        self.assertIn("sheet", kwargs.get("parameters", {}))
        self.assertEqual(kwargs["parameters"]["sheet"], "domestic")


class TestExecutorFiltering(unittest.TestCase):
    """Test pandas local filtering with multiple operators and coercions."""

    def test_apply_filters_basic_operators(self):
        from app.services.tabular.executor import apply_filters

        df = pd.DataFrame([
            {"YEAR": 2024, "TEUS": 100, "LOP": "TIL"},
            {"YEAR": 2023, "TEUS": 150, "LOP": "SPI"},
            {"YEAR": 2024, "TEUS": 200, "LOP": "MSC"},
        ])

        # Test EQ
        f_eq = [FilterCondition(column="YEAR", operator=FilterOperator.EQ, value=2024)]
        res = apply_filters(df.copy(), f_eq)
        self.assertEqual(len(res), 2)

        # Test NEQ
        f_neq = [FilterCondition(column="LOP", operator=FilterOperator.NEQ, value="TIL")]
        res = apply_filters(df.copy(), f_neq)
        self.assertEqual(len(res), 2)
        self.assertNotIn("TIL", res["LOP"].values)

        # Test GT / LT
        f_gt = [FilterCondition(column="TEUS", operator=FilterOperator.GT, value=120)]
        res = apply_filters(df.copy(), f_gt)
        self.assertEqual(len(res), 2)

    def test_apply_filters_contains_and_in(self):
        from app.services.tabular.executor import apply_filters

        df = pd.DataFrame([
            {"LOP": "TIL LINE"},
            {"LOP": "SPI PORT"},
            {"LOP": "MSC GLOBAL"},
        ])

        # Test CONTAINS
        f_contains = [FilterCondition(column="LOP", operator=FilterOperator.CONTAINS, value="line")]
        res = apply_filters(df.copy(), f_contains)
        self.assertEqual(len(res), 1)
        self.assertEqual(res.iloc[0]["LOP"], "TIL LINE")

        # Test IN
        f_in = [FilterCondition(column="LOP", operator=FilterOperator.IN, value=["SPI PORT", "MSC GLOBAL"])]
        res = apply_filters(df.copy(), f_in)
        self.assertEqual(len(res), 2)

    def test_apply_filters_case_insensitive_column_fallback(self):
        from app.services.tabular.executor import apply_filters

        df = pd.DataFrame([
            {"Year": 2024, "teus": 100}
        ])

        # Filter has uppercase "YEAR" and "TEUS", schema has "Year" and "teus"
        filters = [
            FilterCondition(column="YEAR", operator=FilterOperator.EQ, value=2024),
            FilterCondition(column="TEUS", operator=FilterOperator.EQ, value=100)
        ]
        res = apply_filters(df.copy(), filters)
        self.assertEqual(len(res), 1)

    def test_apply_filters_type_coercion(self):
        from app.services.tabular.executor import apply_filters

        df = pd.DataFrame([
            {"TEUS": "100"},  # String representation of number
            {"TEUS": "invalid"},
            {"TEUS": 200}
        ])

        filters = [FilterCondition(column="TEUS", operator=FilterOperator.GT, value=50)]
        res = apply_filters(df.copy(), filters)
        self.assertEqual(len(res), 2)  # "invalid" gets coerced to NaN and filtered out


class TestExecutorAggregation(unittest.TestCase):
    """Test aggregation execution: sum, mean, max, min, count."""

    def test_apply_aggregation_scalar(self):
        from app.services.tabular.executor import apply_aggregation

        df = pd.DataFrame([
            {"TEUS": 100},
            {"TEUS": 200},
            {"TEUS": 300}
        ])

        # Test Sum
        sum_spec = AggregationSpec(func="sum", column="TEUS")
        self.assertEqual(apply_aggregation(df, sum_spec), 600.0)

        # Test Mean
        mean_spec = AggregationSpec(func="mean", column="TEUS")
        self.assertEqual(apply_aggregation(df, mean_spec), 200.0)

        # Test Max / Min
        max_spec = AggregationSpec(func="max", column="TEUS")
        self.assertEqual(apply_aggregation(df, max_spec), 300.0)

        # Test Count
        count_spec = AggregationSpec(func="count")
        self.assertEqual(apply_aggregation(df, count_spec), 3)

    def test_apply_aggregation_grouped(self):
        from app.services.tabular.executor import apply_aggregation

        df = pd.DataFrame([
            {"LOP": "TIL", "TEUS": 100},
            {"LOP": "SPI", "TEUS": 200},
            {"LOP": "TIL", "TEUS": 300}
        ])

        sum_spec = AggregationSpec(func="sum", column="TEUS")
        res = apply_aggregation(df, sum_spec, group_by=["LOP"])

        self.assertIsInstance(res, pd.DataFrame)
        self.assertEqual(len(res), 2)
        # Check grouped sum
        til_sum = res[res["LOP"] == "TIL"]["TEUS"].values[0]
        self.assertEqual(til_sum, 400.0)


class TestExecutorResultQuality(unittest.TestCase):
    """Test ResultQuality mapping logic: VALID, EMPTY, NAN, ALL_ZERO."""

    def test_quality_valid(self):
        from app.services.tabular.executor import assess_quality
        # Non-empty dataframe with numeric values is VALID
        df = pd.DataFrame([{"TEUS": 100.0}])
        self.assertEqual(assess_quality(df, is_group_by=True), ResultQuality.VALID)
        self.assertEqual(assess_quality(100.0, is_group_by=False), ResultQuality.VALID)

    def test_quality_empty(self):
        from app.services.tabular.executor import assess_quality
        df_empty = pd.DataFrame()
        self.assertEqual(assess_quality(df_empty, is_group_by=True), ResultQuality.EMPTY)
        self.assertEqual(assess_quality(None, is_group_by=False), ResultQuality.EMPTY)

    def test_quality_nan(self):
        from app.services.tabular.executor import assess_quality
        df_nan = pd.DataFrame([{"TEUS": pd.NA}])
        self.assertEqual(assess_quality(df_nan, is_group_by=True), ResultQuality.NAN)
        self.assertEqual(assess_quality(float("nan"), is_group_by=False), ResultQuality.NAN)

    def test_quality_all_zero(self):
        from app.services.tabular.executor import assess_quality
        df_zero = pd.DataFrame([{"TEUS": 0.0}])
        self.assertEqual(assess_quality(df_zero, is_group_by=True), ResultQuality.ALL_ZERO)
        self.assertEqual(assess_quality(0.0, is_group_by=False), ResultQuality.ALL_ZERO)


class TestExecutorOrchestration(unittest.TestCase):
    """Test the main entry point: execute_query(source_id, plan)."""

    @patch("app.services.tabular.executor.load_dataframe")
    def test_execute_query_orchestration(self, mock_load):
        from app.services.tabular.executor import execute_query

        # Mock loaded dataframe
        df = pd.DataFrame([
            {"YEAR": 2024, "LOP": "TIL", "TEUS": 100},
            {"YEAR": 2024, "LOP": "SPI", "TEUS": 200},
        ])
        mock_load.return_value = df

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="sum", column="TEUS"),
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        result = execute_query(source_id="dummy-uuid", plan=plan)

        self.assertIsInstance(result, ExecutionResult)
        self.assertEqual(result.quality, ResultQuality.VALID)
        self.assertEqual(result.data, 300.0)
        self.assertEqual(result.row_count, 2)


if __name__ == "__main__":
    unittest.main()
