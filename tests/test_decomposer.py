"""
Unit tests for decomposer.py - query decomposition logic.
TDD: Tests written BEFORE implementation (RED phase).

Phase 2D: Decomposer converts QueryAST → list[SubQuery]
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
)


class TestSimpleDecomposition(unittest.TestCase):
    """Test decomposition of simple queries (no multi-hop)"""
    
    def test_simple_query_one_subquery(self):
        """Simple query should produce exactly one SubQuery"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)]
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa BCH TIL tahun 2024?",
            resolved=ResolvedEntities(operators=["TIL"], metrics=["BCH"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 1)
        self.assertEqual(subqueries[0].step, 1)
        self.assertEqual(subqueries[0].template_type, QueryType.SIMPLE)
        self.assertIsNone(subqueries[0].depends_on)
    
    def test_simple_subquery_contains_question(self):
        """SubQuery should contain original question"""
        from app.services.tabular.decomposer import decompose_query
        
        question = "Berapa TEUS TIL?"
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question=question,
            resolved=ResolvedEntities(),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(subqueries[0].question, question)


class TestAggregationDecomposition(unittest.TestCase):
    """Test decomposition of aggregation queries"""
    
    def test_aggregation_one_subquery(self):
        """Aggregation query should produce one SubQuery"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.AGGREGATION,
            intent=UserIntent.TOTAL_AGGREGATION,
            aggregation=AggregationSpec(func="sum", column="TEUS")
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa total TEUS tahun 2024?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 1)
        self.assertEqual(subqueries[0].template_type, QueryType.AGGREGATION)


class TestRankingDecomposition(unittest.TestCase):
    """Test decomposition of ranking queries"""
    
    def test_ranking_top_one_subquery(self):
        """Ranking TOP_N query should produce one SubQuery"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.RANKING,
            intent=UserIntent.TOP_N,
            aggregation=AggregationSpec(func="max", column="BCH")
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Operator mana yang memiliki BCH tertinggi?",
            resolved=ResolvedEntities(metrics=["BCH"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 1)
        self.assertEqual(subqueries[0].template_type, QueryType.RANKING)
    
    def test_ranking_bottom_one_subquery(self):
        """Ranking BOTTOM_N query should produce one SubQuery"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.RANKING,
            intent=UserIntent.BOTTOM_N,
            aggregation=AggregationSpec(func="min", column="BCH")
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Operator mana yang memiliki BCH terendah?",
            resolved=ResolvedEntities(metrics=["BCH"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 1)


class TestTrendDecomposition(unittest.TestCase):
    """Test decomposition of trend queries"""
    
    def test_trend_one_subquery(self):
        """Trend query should produce one SubQuery"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.TREND,
            intent=UserIntent.TREND_ANALYSIS
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Bagaimana tren TEUS tahun 2024?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 1)
        self.assertEqual(subqueries[0].template_type, QueryType.TREND)


class TestMultiHopDecomposition(unittest.TestCase):
    """Test decomposition of multi-hop queries requiring multiple SubQueries"""
    
    def test_year_comparison_two_subqueries(self):
        """Year comparison should produce two SubQueries"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa selisih TEUS tahun 2024 dan 2025?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        self.assertEqual(len(subqueries), 2)
        self.assertEqual(subqueries[0].step, 1)
        self.assertEqual(subqueries[1].step, 2)
    
    def test_year_comparison_extracts_years(self):
        """Year comparison should extract both years correctly"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa selisih TEUS tahun 2024 dan 2025?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        # First subquery should reference 2024
        self.assertIn("2024", subqueries[0].question)
        # Second subquery should reference 2025
        self.assertIn("2025", subqueries[1].question)
    
    def test_year_comparison_dependency(self):
        """Second SubQuery should depend on first (or both independent)"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa selisih TEUS tahun 2024 dan 2025?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        # First query should have no dependency
        self.assertIsNone(subqueries[0].depends_on)
        # Second query dependency (None = parallel, 1 = sequential)
        self.assertIn(subqueries[1].depends_on, [None, 1])


class TestComparisonDecomposition(unittest.TestCase):
    """Test decomposition distinguishing single-query vs multi-hop comparisons"""
    
    def test_domestic_international_comparison_detection(self):
        """Domestic vs International within same year should NOT always produce 2 SubQueries"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Bandingkan TEUS domestic dan international tahun 2024",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        # Could be 1 SubQuery (grouped) or 2 SubQueries (decomposed)
        # Implementation choice - document in report
        self.assertGreaterEqual(len(subqueries), 1)
    
    def test_multi_year_comparison_requires_decomposition(self):
        """Comparison across different years MUST decompose"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa perbedaan TEUS 2024 dan 2025?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        # Must be at least 2 SubQueries
        self.assertGreaterEqual(len(subqueries), 2)


class TestDecompositionEdgeCases(unittest.TestCase):
    """Test edge cases in decomposition"""
    
    def test_missing_temporal_context_multihop(self):
        """Multi-hop without clear temporal context should still decompose safely"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Bandingkan TEUS A dan B",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        # Should produce at least 1 SubQuery (not crash)
        self.assertGreaterEqual(len(subqueries), 1)
    
    def test_percentage_lookup_no_decomposition(self):
        """Percentage lookup should not decompose"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.PERCENTAGE_LOOKUP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa market share TIL?",
            resolved=ResolvedEntities(operators=["TIL"], metrics=["%"]),
            dataset="Market Share"
        )
        
        self.assertEqual(len(subqueries), 1)


class TestSubQueryStructure(unittest.TestCase):
    """Test that SubQuery objects have correct structure"""
    
    def test_subquery_has_required_fields(self):
        """SubQuery should have step, question, template_type, depends_on"""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa TEUS?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        sq = subqueries[0]
        self.assertIsNotNone(sq.step)
        self.assertIsNotNone(sq.question)
        self.assertIsNotNone(sq.template_type)
        # depends_on can be None
    
    def test_subquery_step_numbering(self):
        """SubQuery steps should be numbered 1, 2, 3..."""
        from app.services.tabular.decomposer import decompose_query
        
        ast = QueryAST(
            query_type=QueryType.MULTI_HOP,
            intent=UserIntent.MULTI_HOP
        )
        
        subqueries = decompose_query(
            ast=ast,
            question="Berapa selisih TEUS 2024 dan 2025?",
            resolved=ResolvedEntities(metrics=["TEUS"]),
            dataset="Overview Vessel"
        )
        
        for i, sq in enumerate(subqueries, start=1):
            self.assertEqual(sq.step, i)


if __name__ == "__main__":
    unittest.main()
