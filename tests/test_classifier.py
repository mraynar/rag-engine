"""
Unit tests for classifier.py - query classification logic.
TDD: Tests written BEFORE implementation (RED phase).

Phase 2B: Classifier converts (Question + ResolvedEntities) → QueryAST
"""
import unittest
from app.services.tabular.domain_models import (
    QueryType,
    UserIntent,
    BuildMethod,
    FilterOperator,
    AggregationSpec,
    ResolvedEntities,
    MonthContext,
)


class TestSimpleValueQueries(unittest.TestCase):
    """Test classification of simple value lookup queries"""
    
    def test_simple_bch_til_query(self):
        """Berapa BCH TIL tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa BCH TIL tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should be SIMPLE or AGGREGATION (both valid for single value)
        self.assertIn(ast.query_type, [QueryType.SIMPLE, QueryType.AGGREGATION])
        self.assertEqual(ast.intent, UserIntent.VALUE_LOOKUP)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
        
        # Should have YEAR filter
        year_filters = [f for f in ast.filters if f.column == "YEAR"]
        self.assertEqual(len(year_filters), 1)
        self.assertEqual(year_filters[0].value, 2024)
    
    def test_simple_teus_query_without_aggregation_keyword(self):
        """Berapa TEUS TIL?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        ast = classify_query(
            question="Berapa TEUS TIL?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.intent, UserIntent.VALUE_LOOKUP)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)


class TestAggregationQueries(unittest.TestCase):
    """Test classification of aggregation queries (total, sum)"""
    
    def test_total_teus_2024(self):
        """Berapa total TEUS tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa total TEUS tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.AGGREGATION)
        self.assertEqual(ast.intent, UserIntent.TOTAL_AGGREGATION)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
        
        # Should have aggregation spec
        self.assertIsNotNone(ast.aggregation)
        self.assertEqual(ast.aggregation.func, "sum")
        self.assertEqual(ast.aggregation.column, "TEUS")
        
        # Should have YEAR filter
        year_filters = [f for f in ast.filters if f.column == "YEAR"]
        self.assertEqual(len(year_filters), 1)
        self.assertEqual(year_filters[0].value, 2024)
    
    def test_total_bch_januari_2024(self):
        """Berapa total BCH Januari 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="Januari", month_code=1, year=2024)
        )
        
        ast = classify_query(
            question="Berapa total BCH Januari 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.AGGREGATION)
        self.assertEqual(ast.intent, UserIntent.TOTAL_AGGREGATION)
        
        # Should have YEAR and MONTH filters
        year_filters = [f for f in ast.filters if f.column == "YEAR"]
        month_filters = [f for f in ast.filters if f.column == "MONTH"]
        self.assertEqual(len(year_filters), 1)
        self.assertEqual(len(month_filters), 1)
        self.assertEqual(month_filters[0].value, "Januari")


class TestRankingQueriesTop(unittest.TestCase):
    """Test classification of ranking queries (tertinggi, maksimal, top)"""
    
    def test_operator_bch_tertinggi_2024(self):
        """Operator mana yang memiliki BCH tertinggi di tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Operator mana yang memiliki BCH tertinggi di tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.TOP_N)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
        
        # Should have aggregation with max
        self.assertIsNotNone(ast.aggregation)
        self.assertEqual(ast.aggregation.func, "max")
        self.assertEqual(ast.aggregation.column, "BCH")
    
    def test_teus_paling_banyak(self):
        """TEUS paling banyak tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="TEUS paling banyak tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.TOP_N)
        self.assertIsNotNone(ast.aggregation)
        self.assertEqual(ast.aggregation.func, "max")


class TestRankingQueriesBottom(unittest.TestCase):
    """Test classification of bottom ranking queries (terendah, minimal, paling sedikit)"""
    
    def test_operator_bch_terendah_2024(self):
        """Operator mana yang memiliki BCH terendah tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Operator mana yang memiliki BCH terendah tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.RANKING)
        self.assertEqual(ast.intent, UserIntent.BOTTOM_N)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
        
        # Should have aggregation with min
        self.assertIsNotNone(ast.aggregation)
        self.assertEqual(ast.aggregation.func, "min")
        self.assertEqual(ast.aggregation.column, "BCH")
    
    def test_paling_sedikit(self):
        """TEUS paling sedikit tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="TEUS paling sedikit tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.intent, UserIntent.BOTTOM_N)
        self.assertIsNotNone(ast.aggregation)
        self.assertEqual(ast.aggregation.func, "min")


class TestComparisonQueries(unittest.TestCase):
    """Test classification of comparison queries requiring multi-hop"""
    
    def test_selisih_teus_2024_2025(self):
        """Berapa selisih TEUS tahun 2024 dan 2025?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"]
        )
        
        ast = classify_query(
            question="Berapa selisih TEUS tahun 2024 dan 2025?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should be COMPARISON or MULTI_HOP
        self.assertIn(ast.query_type, [QueryType.COMPARISON, QueryType.MULTI_HOP])
        self.assertIn(ast.intent, [UserIntent.COMPARISON, UserIntent.MULTI_HOP])
        
        # Should be marked for decomposition (deterministic classification)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
    
    def test_bandingkan_domestic_international(self):
        """Bandingkan TEUS domestic dan international tahun 2024"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Bandingkan TEUS domestic dan international tahun 2024",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertIn(ast.query_type, [QueryType.COMPARISON, QueryType.MULTI_HOP])


class TestTrendQueries(unittest.TestCase):
    """Test classification of trend analysis queries"""
    
    def test_tren_teus_2024(self):
        """Bagaimana tren TEUS tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Bagaimana tren TEUS tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.TREND)
        self.assertEqual(ast.intent, UserIntent.TREND_ANALYSIS)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
    
    def test_perkembangan_bch_per_bulan(self):
        """Perkembangan BCH per bulan tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Perkembangan BCH per bulan tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.TREND)
        self.assertEqual(ast.intent, UserIntent.TREND_ANALYSIS)


class TestPercentageQueries(unittest.TestCase):
    """Test classification of percentage/market share queries"""
    
    def test_market_share_operator(self):
        """Berapa market share operator TIL?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["%"],
            columns=["%"]
        )
        
        ast = classify_query(
            question="Berapa market share operator TIL?",
            resolved=resolved,
            dataset="Market Share"
        )
        
        self.assertEqual(ast.intent, UserIntent.PERCENTAGE_LOOKUP)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)
    
    def test_persentase_market_share(self):
        """Berapa persentase market share TIL tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["%"],
            columns=["%"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa persentase market share TIL tahun 2024?",
            resolved=resolved,
            dataset="Market Share"
        )
        
        self.assertEqual(ast.intent, UserIntent.PERCENTAGE_LOOKUP)


class TestFilterConstruction(unittest.TestCase):
    """Test that classifier creates appropriate filters"""
    
    def test_year_filter_created(self):
        """Year 2024 should create YEAR == 2024 filter"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa total TEUS tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        year_filters = [f for f in ast.filters if f.column == "YEAR"]
        self.assertEqual(len(year_filters), 1)
        self.assertEqual(year_filters[0].operator, FilterOperator.EQ)
        self.assertEqual(year_filters[0].value, 2024)
    
    def test_month_filter_created(self):
        """Januari should create MONTH == Januari filter"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="Januari", month_code=1, year=2024)
        )
        
        ast = classify_query(
            question="Berapa TEUS Januari 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        month_filters = [f for f in ast.filters if f.column == "MONTH"]
        self.assertEqual(len(month_filters), 1)
        self.assertEqual(month_filters[0].value, "Januari")
    
    def test_operator_filter_overview_vessel(self):
        """TIL in Overview Vessel should create LOP == TIL filter"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["BCH"],
            columns=["BCH"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa BCH TIL tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should have operator filter with correct column (LOP for Overview Vessel)
        operator_filters = [f for f in ast.filters if f.column == "LOP"]
        self.assertEqual(len(operator_filters), 1)
        self.assertEqual(operator_filters[0].value, "TIL")
    
    def test_operator_filter_market_share(self):
        """Operator in Market Share uses OPERATOR column"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL"],
            metrics=["%"],
            columns=["%"]
        )
        
        ast = classify_query(
            question="Berapa market share TIL?",
            resolved=resolved,
            dataset="Market Share"
        )
        
        # Should use OPERATOR column for Market Share dataset
        operator_filters = [f for f in ast.filters if f.column == "OPERATOR"]
        self.assertEqual(len(operator_filters), 1)
        self.assertEqual(operator_filters[0].value, "TIL")


class TestAmbiguousQueries(unittest.TestCase):
    """Test that ambiguous questions fall back to LLM"""
    
    def test_vague_question_llm_fallback(self):
        """Bagaimana performa kapal yang paling aktif?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=[],
            columns=[]
        )
        
        ast = classify_query(
            question="Bagaimana performa kapal yang paling aktif?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should fall back to LLM
        self.assertEqual(ast.build_method, BuildMethod.LLM_FALLBACK)
    
    def test_complex_semantic_question(self):
        """Seberapa bagus aktivitas operator dibanding kondisi sebelumnya?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            metrics=[],
            columns=[]
        )
        
        ast = classify_query(
            question="Seberapa bagus aktivitas operator dibanding kondisi sebelumnya?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        # Should fall back to LLM due to vague semantics
        self.assertEqual(ast.build_method, BuildMethod.LLM_FALLBACK)
    
    def test_no_entities_resolved(self):
        """Question with no resolved entities should fall back"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities()
        
        ast = classify_query(
            question="Berapa data terakhir?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.build_method, BuildMethod.LLM_FALLBACK)


class TestMultipleOperators(unittest.TestCase):
    """Test queries with multiple operators"""
    
    def test_til_dan_spi(self):
        """Berapa total TEUS TIL dan SPI tahun 2024?"""
        from app.services.tabular.classifier import classify_query
        
        resolved = ResolvedEntities(
            operators=["TIL", "SPI"],
            metrics=["TEUS"],
            columns=["TEUS"],
            month=MonthContext(month_str="", month_code=0, year=2024)
        )
        
        ast = classify_query(
            question="Berapa total TEUS TIL dan SPI tahun 2024?",
            resolved=resolved,
            dataset="Overview Vessel"
        )
        
        self.assertEqual(ast.query_type, QueryType.AGGREGATION)
        self.assertEqual(ast.intent, UserIntent.TOTAL_AGGREGATION)
        
        # Should have operator filter with IN operator
        lop_filters = [f for f in ast.filters if f.column == "LOP"]
        self.assertEqual(len(lop_filters), 1)
        self.assertEqual(lop_filters[0].operator, FilterOperator.IN)
        self.assertEqual(lop_filters[0].value, ["TIL", "SPI"])


if __name__ == "__main__":
    unittest.main()
