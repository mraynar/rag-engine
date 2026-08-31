"""
Unit tests for resolver.py - entity resolution and routing logic.
TDD: Tests written BEFORE implementation.
"""
import unittest
from app.services.tabular.domain_models import DatasetRouteResult, RoutingMethod, ResolvedEntities, MonthContext


class TestDatasetRouting(unittest.TestCase):
    """Test dataset routing priority chain: P1 → P2 → P3 → P4 → P5"""
    
    def test_p1_explicit_category_name_wins(self):
        """P1: Explicit category_name always wins, even if question suggests otherwise"""
        from app.services.tabular.resolver import route_dataset
        
        result = route_dataset(
            question="Berapa throughput TIL?",
            category_name="Overview Vessel"
        )
        self.assertEqual(result.dataset, "Overview Vessel")
        self.assertEqual(result.method, RoutingMethod.EXPLICIT_PARAM)
    
    def test_p1_explicit_takes_priority_over_keywords(self):
        """P1: Explicit param overrides strong keyword matches"""
        from app.services.tabular.resolver import route_dataset
        
        # Question has "transhipment" keyword but explicit param wins
        result = route_dataset(
            question="Berapa transhipment?",
            category_name="Container Throughput"
        )
        self.assertEqual(result.dataset, "Container Throughput")
        self.assertEqual(result.method, RoutingMethod.EXPLICIT_PARAM)
    
    def test_p2_literal_dataset_name_in_question(self):
        """P2: Question explicitly mentions dataset name"""
        from app.services.tabular.resolver import route_dataset
        
        result = route_dataset(
            question="Berapa data di Overview Vessel tahun 2024?",
            category_name=None
        )
        self.assertEqual(result.dataset, "Overview Vessel")
    
    def test_p4_weighted_keyword_scoring(self):
        """P4: Use keyword scoring from DATASET_REGISTRY"""
        from app.services.tabular.resolver import route_dataset
        
        # "BCH" has high score for Overview Vessel
        result = route_dataset(
            question="Berapa BCH TIL?",
            category_name=None
        )
        self.assertEqual(result.dataset, "Overview Vessel")
    
    def test_p4_transhipment_keyword_exclusive(self):
        """P4: Transhipment keyword routes to Transhipment dataset"""
        from app.services.tabular.resolver import route_dataset
        
        result = route_dataset(
            question="Berapa transhipment 2024?",
            category_name=None
        )
        self.assertEqual(result.dataset, "Transhipment")

    def test_p4_realisasi_uc_keyword_routes_to_tabular_dataset(self):
        """P4: Realisasi UC should route to tabular source even when category is All Data"""
        from app.services.tabular.resolver import route_dataset

        result = route_dataset(
            question="Berapa total realisasi UC?",
            category_name=None
        )
        self.assertEqual(result.dataset, "Realisasi UC")
        self.assertGreater(result.score, 0)

    def test_realisasi_uc_metric_alias_maps_to_total_column(self):
        """Questions mentioning UC or realisasi should resolve to the actual TOTAL column in the dataset."""
        from app.services.tabular.resolver import resolve_entities

        entities = resolve_entities("Berapa total realisasi UC?", dataset="Realisasi UC")
        self.assertIn("TOTAL", entities.metrics)
    
    def test_p5_ambiguous_dataset(self):
        """P5: Multiple datasets have equal evidence"""
        from app.services.tabular.resolver import route_dataset
        
        # Generic question with no strong indicators
        result = route_dataset(
            question="Berapa total tahun 2024?",
            category_name=None
        )
        # Should either pick one or mark as ambiguous
        self.assertIsNotNone(result)


class TestSheetRouting(unittest.TestCase):
    """Test sheet routing using SHEET_REGISTRY"""
    
    def test_overview_vessel_domestic_uppercase(self):
        """Overview Vessel domestic maps to DOMESTIC (uppercase)"""
        from app.services.tabular.resolver import route_sheet
        
        result = route_sheet(
            question="Berapa TEUS domestic?",
            dataset="Overview Vessel"
        )
        self.assertIn("DOMESTIC", result)
    
    def test_overview_vessel_international_uppercase(self):
        """Overview Vessel international maps to INTERNATIONAL (uppercase)"""
        from app.services.tabular.resolver import route_sheet
        
        result = route_sheet(
            question="Berapa TEUS international?",
            dataset="Overview Vessel"
        )
        self.assertIn("INTERNATIONAL", result)
    
    def test_container_throughput_domestik_indonesian(self):
        """Container Throughput domestic maps to Domestik (Indonesian capitalized)"""
        from app.services.tabular.resolver import route_sheet
        
        result = route_sheet(
            question="Berapa throughput domestik?",
            dataset="Container Throughput"
        )
        self.assertIn("Domestik", result)
    
    def test_no_sheet_keyword_returns_all(self):
        """No sheet keyword returns all applicable sheets"""
        from app.services.tabular.resolver import route_sheet
        
        result = route_sheet(
            question="Berapa BCH TIL?",
            dataset="Overview Vessel"
        )
        # Should include both DOMESTIC and INTERNATIONAL or indicate no restriction
        self.assertIsInstance(result, (list, type(None)))
        if isinstance(result, list):
            self.assertGreaterEqual(len(result), 2)


class TestEntityResolution(unittest.TestCase):
    """Test entity resolution from question text"""
    
    def test_single_operator_til(self):
        """Resolve single operator TIL"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa BCH TIL?", dataset="Overview Vessel")
        self.assertIn("TIL", entities.operators)
    
    def test_multiple_operators(self):
        """Resolve multiple operators"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa TEUS TIL dan SPI?", dataset="Overview Vessel")
        self.assertIn("TIL", entities.operators)
        self.assertIn("SPI", entities.operators)
    
    def test_metric_bch(self):
        """Resolve metric BCH"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa BCH tahun 2024?", dataset="Overview Vessel")
        self.assertIn("BCH", entities.metrics)
    
    def test_metric_alias_productivity(self):
        """Resolve productivity → BCH"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa produktivitas TIL?", dataset="Overview Vessel")
        self.assertIn("BCH", entities.metrics)
    
    def test_metric_alias_throughput(self):
        """Resolve throughput → TEUS"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa throughput?", dataset="Overview Vessel")
        self.assertIn("TEUS", entities.metrics)
    
    def test_year_2024(self):
        """Resolve year 2024"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa TEUS tahun 2024?", dataset="Overview Vessel")
        self.assertEqual(entities.month.year, 2024) if entities.month else self.fail("Year not resolved")
    
    def test_month_januari(self):
        """Resolve month Januari"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa TEUS Januari 2024?", dataset="Overview Vessel")
        self.assertIsNotNone(entities.month)
        self.assertEqual(entities.month.month_code, 1)
    
    def test_no_aggregation_interpretation(self):
        """Resolver does NOT interpret tertinggi/terendah/total"""
        from app.services.tabular.resolver import resolve_entities
        
        entities = resolve_entities("Berapa BCH tertinggi?", dataset="Overview Vessel")
        # Should resolve BCH but not the aggregation intent
        self.assertIn("BCH", entities.metrics)


class TestColumnResolution(unittest.TestCase):
    """Test column resolution with schema validation"""
    
    def test_productivity_to_bch(self):
        """Resolve productivity to BCH column"""
        from app.services.tabular.resolver import resolve_columns
        
        columns = resolve_columns(
            metrics=["productivity"],
            dataset="Overview Vessel"
        )
        self.assertIn("BCH", columns)
    
    def test_throughput_to_teus(self):
        """Resolve throughput to TEUS column"""
        from app.services.tabular.resolver import resolve_columns
        
        columns = resolve_columns(
            metrics=["throughput"],
            dataset="Overview Vessel"
        )
        self.assertIn("TEUS", columns)
    
    def test_direct_column_bch(self):
        """Direct column name BCH"""
        from app.services.tabular.resolver import resolve_columns
        
        columns = resolve_columns(
            metrics=["BCH"],
            dataset="Overview Vessel"
        )
        self.assertIn("BCH", columns)
    
    def test_invalid_metric_for_dataset(self):
        """Metric not in dataset returns empty or unresolved"""
        from app.services.tabular.resolver import resolve_columns
        
        columns = resolve_columns(
            metrics=["ACTUAL"],
            dataset="Overview Vessel"
        )
        # ACTUAL is not in Overview Vessel schema
        self.assertNotIn("ACTUAL", columns)


class TestMonthNormalization(unittest.TestCase):
    """Test month normalization using MONTH_NORMALIZE_MAP"""
    
    def test_january_english(self):
        """January → Januari, code 1"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("January")
        self.assertIsNotNone(result)
        self.assertEqual(result.month_str, "Januari")
        self.assertEqual(result.month_code, 1)
    
    def test_januari_indonesian(self):
        """Januari → Januari, code 1"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("Januari")
        self.assertIsNotNone(result)
        self.assertEqual(result.month_str, "Januari")
        self.assertEqual(result.month_code, 1)
    
    def test_jan_abbreviated(self):
        """Jan → Januari, code 1"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("Jan")
        self.assertIsNotNone(result)
        self.assertEqual(result.month_code, 1)
    
    def test_numeric_6(self):
        """6 → Juni, code 6"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("6")
        self.assertIsNotNone(result)
        self.assertEqual(result.month_str, "Juni")
        self.assertEqual(result.month_code, 6)
    
    def test_december(self):
        """December → Desember, code 12"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("December")
        self.assertIsNotNone(result)
        self.assertEqual(result.month_str, "Desember")
        self.assertEqual(result.month_code, 12)
    
    def test_none_input(self):
        """None input returns None"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month(None)
        self.assertIsNone(result)
    
    def test_invalid_month(self):
        """Invalid month string returns None"""
        from app.services.tabular.resolver import normalize_month
        
        result = normalize_month("InvalidMonth")
        self.assertIsNone(result)


class TestResolverRegression(unittest.TestCase):
    def test_ranking_operator_resolution_yang_pronoun(self):
        from app.services.tabular.resolver import resolve_entities
        # "yang" as relative pronoun should NOT be resolved as LOP operator
        res = resolve_entities("Operator mana yang memiliki TEUS tertinggi pada tahun 2024?")
        self.assertNotIn("YANG", res.operators)

    def test_ranking_operator_resolution_yang_explicit(self):
        from app.services.tabular.resolver import resolve_entities
        # If capitalized as Yang or YANG, or matches "Yang Ming", it should match
        res1 = resolve_entities("Berapa TEUS Yang tahun 2024?")
        self.assertIn("YANG", res1.operators)
        
        res2 = resolve_entities("Berapa TEUS YANG tahun 2024?")
        self.assertIn("YANG", res2.operators)
        
        res3 = resolve_entities("Berapa TEUS Yang Ming tahun 2024?")
        self.assertIn("YANG", res3.operators)

        res4 = resolve_entities("Berapa TEUS operator yang tahun 2024?")
        self.assertIn("YANG", res4.operators)

    def test_legitimate_operator_still_resolves(self):
        from app.services.tabular.resolver import resolve_entities
        res = resolve_entities("Berapa TEUS TIL tahun 2024?")
        self.assertIn("TIL", res.operators)

    def test_word_boundaries_no_substring_match(self):
        from app.services.tabular.resolver import resolve_entities
        # "til" is inside "utilisasi", should NOT match TIL operator
        res = resolve_entities("Berapa utilisasi crane pada tahun 2024?")
        self.assertNotIn("TIL", res.operators)


if __name__ == "__main__":
    unittest.main()
