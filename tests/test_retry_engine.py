"""
Unit tests for retry_engine.py - Strategy Pattern retry cascade for tabular query plans.
TDD: Tests written BEFORE implementation.
"""
import unittest
from unittest.mock import MagicMock, patch

from app.services.tabular.domain_models import (
    QueryPlan,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    BuildMethod,
    ExecutionResult,
    ResultQuality,
    ResolvedEntities,
    MonthContext,
    RetryStrategy,
)


class TestRetryEngineOrchestration(unittest.TestCase):
    """Test retry engine loop, budget, and stop conditions."""

    @patch("app.services.tabular.retry_engine.execute_query")
    def test_no_retry_for_valid_result(self, mock_execute):
        """Should return immediately if first execution quality is VALID."""
        from app.services.tabular.retry_engine import execute_with_retry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[],
            aggregation=None,
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        mock_execute.return_value = ExecutionResult(
            data=100,
            quality=ResultQuality.VALID,
            row_count=1
        )

        res = execute_with_retry(
            source_id="dummy-uuid",
            plan=plan,
            question="Berapa TEUS?",
            resolved=ResolvedEntities(),
            dataset="Overview Vessel"
        )

        self.assertEqual(res.quality, ResultQuality.VALID)
        self.assertEqual(res.retry_count, 0)
        mock_execute.assert_called_once()

    @patch("app.services.tabular.retry_engine.execute_query")
    def test_retry_budget_exhausted(self, mock_execute):
        """Should stop and return last result when max_retry_count is reached."""
        from app.services.tabular.retry_engine import execute_with_retry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[
                FilterCondition("YEAR", FilterOperator.EQ, 2024),
                FilterCondition("MONTH", FilterOperator.EQ, "January"),
                FilterCondition("LOP", FilterOperator.EQ, "TIL"),
            ],
            aggregation=AggregationSpec(func="max", column="TEUS"),
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        # Always return EMPTY quality
        mock_execute.return_value = ExecutionResult(
            data=None,
            quality=ResultQuality.EMPTY,
            row_count=0
        )

        res = execute_with_retry(
            source_id="dummy-uuid",
            plan=plan,
            question="Berapa TEUS?",
            resolved=ResolvedEntities(
                month=MonthContext("January", 1, 2024),
                operators=["TIL"]
            ),
            dataset="Overview Vessel",
            max_retries=3
        )

        self.assertEqual(res.quality, ResultQuality.EMPTY)
        # Should execute original plan (1) + retries (3) = 4 executions total
        self.assertEqual(mock_execute.call_count, 4)
        self.assertEqual(res.retry_count, 3)

    @patch("app.services.tabular.retry_engine.execute_query")
    def test_retry_stops_on_valid(self, mock_execute):
        """Should stop retry cascade as soon as a strategy yields a VALID result."""
        from app.services.tabular.retry_engine import execute_with_retry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[FilterCondition("MONTH", FilterOperator.EQ, "January")],
            aggregation=None,
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        # First run: EMPTY
        # Second run (after MonthRetry): VALID
        mock_execute.side_effect = [
            ExecutionResult(data=None, quality=ResultQuality.EMPTY, row_count=0),
            ExecutionResult(data=100.0, quality=ResultQuality.VALID, row_count=1),
        ]

        res = execute_with_retry(
            source_id="dummy-uuid",
            plan=plan,
            question="Berapa TEUS?",
            resolved=ResolvedEntities(month=MonthContext("January", 1, 2024)),
            dataset="Overview Vessel"
        )

        self.assertEqual(res.quality, ResultQuality.VALID)
        self.assertEqual(res.data, 100.0)
        self.assertEqual(res.retry_count, 1)
        self.assertEqual(res.last_retry_strategy, RetryStrategy.MONTH_RETRY)


class TestRetryStrategies(unittest.TestCase):
    """Test each RetryStrategy class independently."""

    def test_month_retry_strategy(self):
        """Should convert English or numeric month to Indonesian string in filter."""
        from app.services.tabular.retry_engine import MonthRetry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[FilterCondition("MONTH", FilterOperator.EQ, "January")],
            aggregation=None,
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        strategy = MonthRetry()
        new_plan = strategy.apply(
            plan=plan,
            resolved=ResolvedEntities(month=MonthContext("January", 1, 2024)),
            schema={"columns": ["MONTH", "YEAR"]}
        )

        self.assertIsNotNone(new_plan)
        # Check that month was converted to "Januari"
        month_filter = next(f for f in new_plan.filters if f.column == "MONTH")
        self.assertEqual(month_filter.value, "Januari")

    def test_sheet_retry_strategy(self):
        """Should try alternative sheet in SHEET_REGISTRY."""
        from app.services.tabular.retry_engine import SheetRetry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[],
            aggregation=None,
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        strategy = SheetRetry()
        new_plan = strategy.apply(
            plan=plan,
            resolved=ResolvedEntities(),
            schema={"sheets": ["DOMESTIC", "INTERNATIONAL"]}
        )

        self.assertIsNotNone(new_plan)
        # DOMESTIC fallback tried INTERNATIONAL
        self.assertEqual(new_plan.sheet, "INTERNATIONAL")

    def test_column_retry_strategy(self):
        """Should resolve metric to fallback column alias if original has no match."""
        from app.services.tabular.retry_engine import ColumnRetry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[],
            aggregation=AggregationSpec(func="sum", column="throughput"),
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        strategy = ColumnRetry()
        new_plan = strategy.apply(
            plan=plan,
            resolved=ResolvedEntities(metrics=["throughput"]),
            schema={"columns": ["TEUS", "YEAR"]}
        )

        self.assertIsNotNone(new_plan)
        # "throughput" mapped to "TEUS" in Overview Vessel / Container Throughput
        self.assertEqual(new_plan.aggregation.column, "TEUS")

    def test_relaxed_filter_retry_strategy(self):
        """Should remove the most restrictive/non-essential filter progressively."""
        from app.services.tabular.retry_engine import RelaxedFilterRetry

        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[
                FilterCondition("YEAR", FilterOperator.EQ, 2024),
                FilterCondition("MONTH", FilterOperator.EQ, "Januari"),
                FilterCondition("LOP", FilterOperator.EQ, "TIL"),
            ],
            aggregation=None,
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )

        strategy = RelaxedFilterRetry()
        # Should progressively relax one non-essential filter (e.g. LOP or MONTH)
        new_plan = strategy.apply(
            plan=plan,
            resolved=ResolvedEntities(),
            schema={"columns": ["YEAR", "MONTH", "LOP"]}
        )

        self.assertIsNotNone(new_plan)
        # One filter removed (e.g., LOP or MONTH)
        self.assertEqual(len(new_plan.filters), 2)
        # Should preserve core temporal context (YEAR) if possible
        year_filter = next((f for f in new_plan.filters if f.column == "YEAR"), None)
        self.assertIsNotNone(year_filter)


if __name__ == "__main__":
    unittest.main()
