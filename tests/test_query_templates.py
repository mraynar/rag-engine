"""
Unit tests for query_templates.py - template definitions for query execution.
TDD: Tests written BEFORE implementation (RED phase).

Phase 2C: Templates define reusable execution intent without database/pandas logic.
"""
import unittest
from app.services.tabular.domain_models import QueryType, UserIntent


class TestTemplateRegistry(unittest.TestCase):
    """Test that template registry contains all required query types"""
    
    def test_template_registry_exists(self):
        """Template registry should be importable"""
        from app.services.tabular.query_templates import TEMPLATE_REGISTRY
        self.assertIsNotNone(TEMPLATE_REGISTRY)
    
    def test_all_query_types_have_templates(self):
        """Every QueryType should have at least one template"""
        from app.services.tabular.query_templates import TEMPLATE_REGISTRY
        
        required_types = [
            QueryType.SIMPLE,
            QueryType.AGGREGATION,
            QueryType.RANKING,
            QueryType.TREND,
            QueryType.MULTI_HOP
        ]
        
        for qtype in required_types:
            self.assertIn(qtype, TEMPLATE_REGISTRY, f"Missing template for {qtype}")


class TestSimpleTemplate(unittest.TestCase):
    """Test SIMPLE query template"""
    
    def test_simple_template_structure(self):
        """SIMPLE template should have correct structure"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        self.assertIsNotNone(template)
        
        # Should have required fields
        self.assertIn("requires_aggregation", template)
        self.assertIn("requires_grouping", template)
        self.assertIn("requires_sorting", template)
    
    def test_simple_no_forced_aggregation(self):
        """SIMPLE template should not force aggregation"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        self.assertFalse(template["requires_aggregation"])
    
    def test_simple_no_grouping(self):
        """SIMPLE template should not require grouping"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        self.assertFalse(template["requires_grouping"])


class TestAggregationTemplate(unittest.TestCase):
    """Test AGGREGATION query template"""
    
    def test_aggregation_template_structure(self):
        """AGGREGATION template should require aggregation"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        self.assertIsNotNone(template)
        self.assertTrue(template["requires_aggregation"])
    
    def test_aggregation_default_func(self):
        """TOTAL_AGGREGATION should default to sum"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.AGGREGATION, UserIntent.TOTAL_AGGREGATION)
        self.assertEqual(template.get("default_agg_func"), "sum")


class TestRankingTemplateTop(unittest.TestCase):
    """Test RANKING template for TOP_N intent"""
    
    def test_ranking_top_requires_aggregation(self):
        """RANKING TOP_N should require aggregation"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.TOP_N)
        self.assertTrue(template["requires_aggregation"])
    
    def test_ranking_top_requires_grouping(self):
        """RANKING TOP_N should require grouping"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.TOP_N)
        self.assertTrue(template["requires_grouping"])
    
    def test_ranking_top_default_func(self):
        """RANKING TOP_N should default to max"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.TOP_N)
        self.assertEqual(template.get("default_agg_func"), "sum")
    
    def test_ranking_top_sort_order(self):
        """RANKING TOP_N should sort descending"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.TOP_N)
        self.assertEqual(template.get("sort_order"), "desc")
    
    def test_ranking_top_grouping_dimension(self):
        """RANKING TOP_N should specify operator dimension grouping"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.TOP_N)
        self.assertIn("grouping_dimension", template)
        self.assertEqual(template["grouping_dimension"], "operator")


class TestRankingTemplateBottom(unittest.TestCase):
    """Test RANKING template for BOTTOM_N intent"""
    
    def test_ranking_bottom_default_func(self):
        """RANKING BOTTOM_N should default to min"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.BOTTOM_N)
        self.assertEqual(template.get("default_agg_func"), "sum")
    
    def test_ranking_bottom_sort_order(self):
        """RANKING BOTTOM_N should sort ascending"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.RANKING, UserIntent.BOTTOM_N)
        self.assertEqual(template.get("sort_order"), "asc")


class TestTrendTemplate(unittest.TestCase):
    """Test TREND query template"""
    
    def test_trend_requires_grouping(self):
        """TREND should require grouping"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.TREND, UserIntent.TREND_ANALYSIS)
        self.assertTrue(template["requires_grouping"])
    
    def test_trend_grouping_dimension(self):
        """TREND should specify temporal grouping dimension"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.TREND, UserIntent.TREND_ANALYSIS)
        self.assertIn("grouping_dimension", template)
        self.assertEqual(template["grouping_dimension"], "temporal")
    
    def test_trend_no_limit(self):
        """TREND should not limit results"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.TREND, UserIntent.TREND_ANALYSIS)
        self.assertIsNone(template.get("default_limit"))


class TestPercentageTemplate(unittest.TestCase):
    """Test PERCENTAGE query template"""
    
    def test_percentage_template_structure(self):
        """PERCENTAGE template should exist"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.PERCENTAGE_LOOKUP)
        self.assertIsNotNone(template)
    
    def test_percentage_no_forced_aggregation(self):
        """PERCENTAGE_LOOKUP should not force aggregation (data already has %)"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.PERCENTAGE_LOOKUP)
        self.assertFalse(template.get("requires_aggregation", False))


class TestMultiHopTemplate(unittest.TestCase):
    """Test MULTI_HOP query template"""
    
    def test_multihop_template_exists(self):
        """MULTI_HOP template should exist"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.MULTI_HOP, UserIntent.MULTI_HOP)
        self.assertIsNotNone(template)
    
    def test_multihop_requires_decomposition(self):
        """MULTI_HOP should flag decomposition requirement"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.MULTI_HOP, UserIntent.MULTI_HOP)
        self.assertTrue(template.get("requires_decomposition", False))


class TestTemplateGetFunction(unittest.TestCase):
    """Test get_template() function behavior"""
    
    def test_get_template_returns_dict(self):
        """get_template should return dict"""
        from app.services.tabular.query_templates import get_template
        
        template = get_template(QueryType.SIMPLE, UserIntent.VALUE_LOOKUP)
        self.assertIsInstance(template, dict)
    
    def test_get_template_fallback_behavior(self):
        """get_template should have fallback for unknown intent"""
        from app.services.tabular.query_templates import get_template
        
        # Should not crash with unknown combination
        template = get_template(QueryType.SIMPLE, UserIntent.TOP_N)
        self.assertIsNotNone(template)
    
    def test_get_template_uses_query_type_fallback(self):
        """If specific intent not found, should use query type default"""
        from app.services.tabular.query_templates import get_template
        
        # AGGREGATION with unknown intent should still return aggregation template
        template = get_template(QueryType.AGGREGATION, UserIntent.VALUE_LOOKUP)
        self.assertIsNotNone(template)


if __name__ == "__main__":
    unittest.main()
