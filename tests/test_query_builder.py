"""
Unit tests for query_builder.py - QueryPlan construction from QueryAST.
TDD: Tests written BEFORE implementation (RED phase).

Phase 2E: Query Builder converts QueryAST + Template + ResolvedEntities + Schema → QueryPlan
"""
import unittest
from app.services.tabular.domain_models import (
    QueryAST,
    QueryType,
    UserIntent,
    BuildMethod,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    MonthContext,
    ResolvedEntities,
    SubQuery,
)


class TestBasicQueryBuilding(unittest.TestCase):
    """Test basic query plan building for simple cases"""
    
    def test_simple_value_lookup(self):
        """Simple VALUE_LOOKUP should not force aggregation"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["BCH"],
            columns=["BCH"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa BCH TIL tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should not have aggregation for SIMPLE query
        self.assertIsNone(plan.aggregation)
        self.assertEqual(plan.build_method, BuildMethod.DETERMINISTIC)
    
    def test_sum_aggregation(self):
        """SUM aggregation should be preserved"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="sum", column="TEUS")
        )
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa total TEUS tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertIsNotNone(plan.aggregation)
        self.assertEqual(plan.aggregation.func, "sum")
        self.assertEqual(plan.aggregation.column, "TEUS")
    
    def test_top_ranking(self):
        """TOP_N ranking should have max aggregation, grouping, sorting"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.RANKING,
            intent=UserIntent.TOP_N,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="max", column="BCH")
        )
        
        resolved = ResolvedEntities(
            metrics=["BCH"],
            columns=["BCH"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Operator mana yang memiliki BCH tertinggi tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(plan.aggregation.func, "max")
        self.assertIsNotNone(plan.group_by)
        self.assertEqual(plan.sort, "desc")
        self.assertEqual(plan.limit, 1)
    
    def test_bottom_ranking(self):
        """BOTTOM_N ranking should have min aggregation, asc sort"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.RANKING,
            intent=UserIntent.BOTTOM_N,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="min", column="BCH")
        )
        
        resolved = ResolvedEntities(metrics=["BCH"], columns=["BCH"])
        
        plan = build_query_plan(
            ast=ast,
            question="Operator mana yang memiliki BCH terendah tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(plan.aggregation.func, "min")
        self.assertEqual(plan.sort, "asc")


class TestDatasetAwareColumnResolution(unittest.TestCase):
    """Test dataset-specific operator column resolution"""
    
    def test_overview_vessel_uses_lop(self):
        """Overview Vessel should use LOP column for operators"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["BCH"],
            columns=["BCH"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa BCH TIL tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should have operator filter using LOP column
        lop_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].value, "TIL")
    
    def test_market_share_uses_operator(self):
        """Market Share should use OPERATOR column for operators"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.PERCENTAGE_LOOKUP,
            filters=[]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["%"],
            columns=["%"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa market share TIL?",
            resolved=resolved,
            dataset="Market Share"
        )
        
        # Should have operator filter using LOP column
        op_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(op_filters), 1)
        self.assertEqual(op_filters[0].value, "TIL")


class TestFilterHandling(unittest.TestCase):
    """Test filter construction and preservation"""
    
    def test_year_filter_preserved(self):
        """YEAR filter should be preserved in QueryPlan"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="sum", column="TEUS")
        )
        
        resolved = ResolvedEntities(metrics=["TEUS"], columns=["TEUS"])
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa total TEUS tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        year_filters = [f for f in plan.filters if f.column == "YEAR"]
        self.assertEqual(len(year_filters), 1)
        self.assertEqual(year_filters[0].value, 2024)
    
    def test_month_filter_preserved(self):
        """MONTH filter should be preserved"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[
                FilterCondition("YEAR", FilterOperator.EQ, 2024),
                FilterCondition("MONTH", FilterOperator.EQ, "Januari")
            ]
        )
        
        resolved = ResolvedEntities(metrics=["TEUS"], columns=["TEUS"])
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa TEUS Januari 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        month_filters = [f for f in plan.filters if f.column == "MONTH"]
        self.assertEqual(len(month_filters), 1)
        self.assertEqual(month_filters[0].value, "Januari")
    
    def test_single_operator_filter(self):
        """Single operator should use EQ filter"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa TEUS TIL?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        lop_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].operator, FilterOperator.EQ)
    
    def test_multiple_operators_use_in(self):
        """Multiple operators should use IN filter"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[],
            aggregation=AggregationSpec(func="sum", column="TEUS")
        )
        
        resolved = ResolvedEntities(
            operators=["TIL", "SPI"],
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa total TEUS TIL dan SPI?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        lop_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].operator, FilterOperator.IN)
        self.assertEqual(lop_filters[0].value, ["TIL", "SPI"])
    
    def test_multiple_filters_combined(self):
        """Multiple filters should all be preserved"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[
                FilterCondition("YEAR", FilterOperator.EQ, 2024),
                FilterCondition("MONTH", FilterOperator.EQ, "Januari")
            ]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["BCH"],
            columns=["BCH"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa BCH TIL Januari 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should have YEAR, MONTH, and LOP filters
        self.assertGreaterEqual(len(plan.filters), 3)


class TestEntityPreservation(unittest.TestCase):
    """Test critical entity preservation for multi-hop queries"""
    
    def test_operator_preserved_in_subquery(self):
        """Operator from original query must survive SubQuery decomposition"""
        from app.services.tabular.query_builder import build_query_plan
        
        # Original resolved entities have TIL
        original_resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        # SubQuery question loses TIL
        subquery = SubQuery(
            step=1,
            question="Berapa TEUS tahun 2024?",
            template_type=QueryType.AGGREGATION,
            depends_on=None
        )
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="sum", column="TEUS")
        )
        
        plan = build_query_plan(
            ast=ast,
            question=subquery.question,
            resolved=original_resolved,
            dataset="Overview Vessel",
            subquery=subquery
        )
        
        # CRITICAL: Plan must include TIL operator filter
        lop_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].value, "TIL")
    
    def test_metric_preserved_in_subquery(self):
        """Metric from original query must survive SubQuery"""
        from app.services.tabular.query_builder import build_query_plan
        
        original_resolved = ResolvedEntities(
            operators=["MSC"],
            metrics=["BCH"],
            columns=["BCH"]
        )
        
        subquery = SubQuery(
            step=2,
            question="Berapa tahun 2025?",
            template_type=QueryType.AGGREGATION,
            depends_on=None
        )
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2025)],
            aggregation=AggregationSpec(func="sum", column="BCH")
        )
        
        plan = build_query_plan(
            ast=ast,
            question=subquery.question,
            resolved=original_resolved,
            dataset="Overview Vessel",
            subquery=subquery
        )
        
        # Metric should be preserved
        self.assertEqual(plan.aggregation.column, "BCH")
        
        # Operator should be preserved
        lop_filters = [f for f in plan.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].value, "MSC")


class TestGroupByHandling(unittest.TestCase):
    """Test GROUP BY column resolution"""
    
    def test_ranking_includes_operator_grouping(self):
        """Ranking queries must group by operator dimension"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.RANKING,
            intent=UserIntent.TOP_N,
            filters=[],
            aggregation=AggregationSpec(func="max", column="BCH")
        )
        
        resolved = ResolvedEntities(metrics=["BCH"], columns=["BCH"])
        
        plan = build_query_plan(
            ast=ast,
            question="Operator mana yang memiliki BCH tertinggi?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertIsNotNone(plan.group_by)
        self.assertIn("LOP", plan.group_by)
    
    def test_trend_monthly_grouping(self):
        """Trend 'per bulan' should group by MONTH"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.TREND,
            intent=UserIntent.TREND_ANALYSIS,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)]
        )
        
        resolved = ResolvedEntities(metrics=["TEUS"], columns=["TEUS"])
        
        plan = build_query_plan(
            ast=ast,
            question="Perkembangan TEUS per bulan tahun 2024",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertIsNotNone(plan.group_by)
        self.assertIn("MONTH", plan.group_by)
    
    def test_trend_yearly_grouping(self):
        """Trend 'per tahun' should group by YEAR"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.TREND,
            intent=UserIntent.TREND_ANALYSIS,
            filters=[]
        )
        
        resolved = ResolvedEntities(metrics=["TEUS"], columns=["TEUS"])
        
        plan = build_query_plan(
            ast=ast,
            question="Perkembangan TEUS per tahun",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertIsNotNone(plan.group_by)
        self.assertIn("YEAR", plan.group_by)


class TestSchemaValidation(unittest.TestCase):
    """Test schema validation prevents invalid QueryPlans"""
    
    def test_invalid_aggregation_column_rejected(self):
        """Invalid aggregation column should cause controlled failure"""
        from app.services.tabular.query_builder import build_query_plan, QueryBuildError
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            filters=[],
            aggregation=AggregationSpec(func="sum", column="INVALID_COL")
        )
        
        resolved = ResolvedEntities(metrics=["INVALID_COL"], columns=["INVALID_COL"])
        
        with self.assertRaises(QueryBuildError):
            build_query_plan(
                ast=ast,
                question="Berapa total INVALID_COL?",
                resolved=resolved,
                dataset="Overview Vessel"
            )
    
    def test_invalid_filter_column_rejected(self):
        """Invalid filter column should cause controlled failure"""
        from app.services.tabular.query_builder import build_query_plan, QueryBuildError
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[FilterCondition("INVALID_COL", FilterOperator.EQ, "value")]
        )
        
        resolved = ResolvedEntities()
        
        with self.assertRaises(QueryBuildError):
            build_query_plan(
                ast=ast,
                question="Test query",
                resolved=resolved,
                dataset="Overview Vessel"
            )


class TestPercentageQuery(unittest.TestCase):
    """Test percentage lookup queries"""
    
    def test_percentage_lookup_no_aggregation(self):
        """Percentage lookup should not add aggregation"""
        from app.services.tabular.query_builder import build_query_plan
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.PERCENTAGE_LOOKUP,
            filters=[]
        )
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["%"],
            columns=["%"]
        )
        
        plan = build_query_plan(
            ast=ast,
            question="Berapa market share TIL?",
            resolved=resolved,
            dataset="Market Share"
        )
        
        # Should not have aggregation (data already has %)
        self.assertIsNone(plan.aggregation)


if __name__ == "__main__":
    unittest.main()
