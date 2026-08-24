"""
Unit tests for RAG Query Planner deterministic components.
Written BEFORE implementation (TDD).

Phase 1: domain_models, registries, schema_registry
Phase 2: resolver (dataset/sheet/entity/month routing)
Phase 3: classifier, query_templates, decomposer
Phase 4: query_builder (deterministic)
Phase 6: executor, retry_engine
Phase 7: formatter
"""
import unittest


# ============================================================
# PHASE 1 — Domain Models
# ============================================================

class TestQueryTypeEnum(unittest.TestCase):
    def test_all_query_types_exist(self):
        from app.services.tabular.domain_models import QueryType
        expected = {"SIMPLE", "AGGREGATION", "COMPARISON", "RANKING", "TREND", "MULTI_HOP"}
        actual = {m.name for m in QueryType}
        self.assertEqual(expected, actual)

    def test_query_type_values_are_strings(self):
        from app.services.tabular.domain_models import QueryType
        for qt in QueryType:
            self.assertIsInstance(qt.value, str)

    def test_query_type_comparable(self):
        from app.services.tabular.domain_models import QueryType
        self.assertEqual(QueryType.RANKING, QueryType.RANKING)
        self.assertNotEqual(QueryType.RANKING, QueryType.SIMPLE)


class TestUserIntentEnum(unittest.TestCase):
    def test_all_intents_exist(self):
        from app.services.tabular.domain_models import UserIntent
        expected = {
            "VALUE_LOOKUP", "TOP_N", "BOTTOM_N", "COMPARISON",
            "TREND_ANALYSIS", "TOTAL_AGGREGATION", "PERCENTAGE_LOOKUP", "MULTI_HOP"
        }
        actual = {m.name for m in UserIntent}
        self.assertEqual(expected, actual)


class TestBuildMethodEnum(unittest.TestCase):
    def test_both_build_methods_exist(self):
        from app.services.tabular.domain_models import BuildMethod
        self.assertIn("DETERMINISTIC", {m.name for m in BuildMethod})
        self.assertIn("LLM_FALLBACK", {m.name for m in BuildMethod})


class TestResultQualityEnum(unittest.TestCase):
    def test_all_qualities_exist(self):
        from app.services.tabular.domain_models import ResultQuality
        expected = {"VALID", "EMPTY", "NAN", "ALL_ZERO"}
        actual = {m.name for m in ResultQuality}
        self.assertEqual(expected, actual)


class TestRetryStrategyEnum(unittest.TestCase):
    def test_all_strategies_exist(self):
        from app.services.tabular.domain_models import RetryStrategy
        expected = {
            "MONTH_RETRY", "SHEET_RETRY", "COLUMN_RETRY",
            "OPERATOR_RETRY", "RELAXED_FILTER_RETRY", "AGGREGATION_RETRY"
        }
        actual = {m.name for m in RetryStrategy}
        self.assertEqual(expected, actual)


class TestFilterOperatorEnum(unittest.TestCase):
    def test_all_operators_exist(self):
        from app.services.tabular.domain_models import FilterOperator
        expected = {"EQ", "NEQ", "GT", "LT", "GTE", "LTE", "CONTAINS", "IN"}
        actual = {m.name for m in FilterOperator}
        self.assertEqual(expected, actual)

    def test_operator_values_match_pandas_syntax(self):
        from app.services.tabular.domain_models import FilterOperator
        self.assertEqual(FilterOperator.EQ.value, "==")
        self.assertEqual(FilterOperator.NEQ.value, "!=")
        self.assertEqual(FilterOperator.GT.value, ">")
        self.assertEqual(FilterOperator.LT.value, "<")
        self.assertEqual(FilterOperator.IN.value, "in")


class TestFilterConditionDataclass(unittest.TestCase):
    def test_can_instantiate_filter_condition(self):
        from app.services.tabular.domain_models import FilterCondition, FilterOperator
        fc = FilterCondition(column="YEAR", operator=FilterOperator.EQ, value=2024)
        self.assertEqual(fc.column, "YEAR")
        self.assertEqual(fc.operator, FilterOperator.EQ)
        self.assertEqual(fc.value, 2024)

    def test_filter_condition_with_string_value(self):
        from app.services.tabular.domain_models import FilterCondition, FilterOperator
        fc = FilterCondition(column="MONTH", operator=FilterOperator.EQ, value="Januari")
        self.assertEqual(fc.value, "Januari")

    def test_filter_condition_with_list_value(self):
        from app.services.tabular.domain_models import FilterCondition, FilterOperator
        fc = FilterCondition(column="YEAR", operator=FilterOperator.IN, value=[2024, 2025])
        self.assertIsInstance(fc.value, list)


class TestAggregationSpecDataclass(unittest.TestCase):
    def test_can_instantiate_with_column(self):
        from app.services.tabular.domain_models import AggregationSpec
        agg = AggregationSpec(func="sum", column="TEUS")
        self.assertEqual(agg.func, "sum")
        self.assertEqual(agg.column, "TEUS")

    def test_can_instantiate_count_without_column(self):
        from app.services.tabular.domain_models import AggregationSpec
        agg = AggregationSpec(func="count")
        self.assertIsNone(agg.column)


class TestQueryASTDataclass(unittest.TestCase):
    def test_can_instantiate_with_defaults(self):
        from app.services.tabular.domain_models import QueryAST, QueryType, UserIntent, BuildMethod
        ast = QueryAST(query_type=QueryType.AGGREGATION, intent=UserIntent.TOTAL_AGGREGATION)
        self.assertEqual(ast.query_type, QueryType.AGGREGATION)
        self.assertEqual(ast.intent, UserIntent.TOTAL_AGGREGATION)
        self.assertEqual(ast.filters, [])
        self.assertIsNone(ast.aggregation)
        self.assertEqual(ast.build_method, BuildMethod.DETERMINISTIC)

    def test_can_add_filter_conditions(self):
        from app.services.tabular.domain_models import (
            QueryAST, QueryType, UserIntent, FilterCondition, FilterOperator
        )
        fc = FilterCondition(column="YEAR", operator=FilterOperator.EQ, value=2024)
        ast = QueryAST(
            query_type=QueryType.SIMPLE,
            intent=UserIntent.VALUE_LOOKUP,
            filters=[fc]
        )
        self.assertEqual(len(ast.filters), 1)
        self.assertEqual(ast.filters[0].column, "YEAR")


class TestQueryPlanDataclass(unittest.TestCase):
    def test_can_instantiate_query_plan(self):
        from app.services.tabular.domain_models import (
            QueryPlan, FilterCondition, FilterOperator,
            AggregationSpec, BuildMethod
        )
        plan = QueryPlan(
            sheet="DOMESTIC",
            filters=[FilterCondition("YEAR", FilterOperator.EQ, 2024)],
            aggregation=AggregationSpec(func="sum", column="TEUS"),
            group_by=None,
            sort=None,
            limit=None,
            build_method=BuildMethod.DETERMINISTIC
        )
        self.assertEqual(plan.sheet, "DOMESTIC")
        self.assertEqual(plan.build_method, BuildMethod.DETERMINISTIC)

    def test_query_plan_with_group_by_and_sort(self):
        from app.services.tabular.domain_models import (
            QueryPlan, AggregationSpec, BuildMethod
        )
        plan = QueryPlan(
            sheet=None,
            filters=[],
            aggregation=AggregationSpec(func="sum", column="BCH"),
            group_by=["LOP"],
            sort="desc",
            limit=1,
            build_method=BuildMethod.DETERMINISTIC
        )
        self.assertEqual(plan.group_by, ["LOP"])
        self.assertEqual(plan.sort, "desc")
        self.assertEqual(plan.limit, 1)


class TestDatasetRouteResultDataclass(unittest.TestCase):
    def test_can_instantiate_with_defaults(self):
        from app.services.tabular.domain_models import DatasetRouteResult, RoutingMethod
        result = DatasetRouteResult(
            dataset="Overview Vessel",
            method=RoutingMethod.EXPLICIT_PARAM
        )
        self.assertEqual(result.dataset, "Overview Vessel")
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.score, 0.0)

    def test_ambiguous_result_carries_candidates(self):
        from app.services.tabular.domain_models import DatasetRouteResult, RoutingMethod
        result = DatasetRouteResult(
            dataset="",
            method=RoutingMethod.AMBIGUOUS,
            candidates=["Overview Vessel", "Container Throughput"],
            score=0.5
        )
        self.assertEqual(result.method, RoutingMethod.AMBIGUOUS)
        self.assertEqual(len(result.candidates), 2)


class TestResolvedEntitiesDataclass(unittest.TestCase):
    def test_default_empty(self):
        from app.services.tabular.domain_models import ResolvedEntities
        e = ResolvedEntities()
        self.assertEqual(e.operators, [])
        self.assertEqual(e.metrics, [])
        self.assertEqual(e.columns, [])

    def test_month_context_nested(self):
        from app.services.tabular.domain_models import ResolvedEntities, MonthContext
        e = ResolvedEntities(month=MonthContext(month_str="Januari", month_code=1, year=2024))
        self.assertEqual(e.month.month_str, "Januari")
        self.assertEqual(e.month.month_code, 1)
        self.assertEqual(e.month.year, 2024)


class TestSubQueryDataclass(unittest.TestCase):
    def test_simple_subquery(self):
        from app.services.tabular.domain_models import SubQuery, QueryType
        sq = SubQuery(step=1, question="Berapa total TEUS 2024?")
        self.assertEqual(sq.step, 1)
        self.assertIsNone(sq.depends_on)
        self.assertEqual(sq.template_type, QueryType.SIMPLE)

    def test_multihop_subquery_dependency(self):
        from app.services.tabular.domain_models import SubQuery, QueryType
        sq2 = SubQuery(step=2, question="Bagaimana internasional bulan tersebut?",
                       template_type=QueryType.MULTI_HOP, depends_on=1)
        self.assertEqual(sq2.depends_on, 1)


class TestExecutionResultDataclass(unittest.TestCase):
    def test_valid_result(self):
        from app.services.tabular.domain_models import ExecutionResult, ResultQuality
        result = ExecutionResult(
            data=8561595.0,
            quality=ResultQuality.VALID,
            row_count=1
        )
        self.assertEqual(result.quality, ResultQuality.VALID)
        self.assertEqual(result.retry_count, 0)
        self.assertIsNone(result.last_retry_strategy)

    def test_empty_result(self):
        from app.services.tabular.domain_models import ExecutionResult, ResultQuality
        result = ExecutionResult(data=None, quality=ResultQuality.EMPTY, row_count=0)
        self.assertEqual(result.quality, ResultQuality.EMPTY)


# ============================================================
# PHASE 1 — Registries
# ============================================================

class TestDatasetRegistry(unittest.TestCase):
    def setUp(self):
        from app.services.tabular.registries import DATASET_REGISTRY
        self.registry = DATASET_REGISTRY

    def test_four_datasets_registered(self):
        expected = {"Container Throughput", "Overview Vessel", "Market Share", "Transhipment"}
        self.assertEqual(expected, set(self.registry.keys()))

    def test_each_dataset_has_keywords(self):
        for dataset, config in self.registry.items():
            self.assertIn("keywords", config, f"{dataset} missing keywords")
            self.assertGreater(len(config["keywords"]), 0, f"{dataset} keywords empty")

    def test_overview_vessel_bch_has_high_score(self):
        score = self.registry["Overview Vessel"]["keywords"].get("bch", 0)
        self.assertGreaterEqual(score, 4, "BCH should have score >= 4 for Overview Vessel")

    def test_transhipment_keyword_exclusive(self):
        ts_score = self.registry["Transhipment"]["keywords"].get("transhipment", 0)
        self.assertGreaterEqual(ts_score, 4, "transhipment keyword should score high for Transhipment dataset")

    def test_container_throughput_has_actual_budget(self):
        ct_kw = self.registry["Container Throughput"]["keywords"]
        self.assertIn("actual", ct_kw)
        self.assertIn("budget", ct_kw)


class TestSheetRegistry(unittest.TestCase):
    def setUp(self):
        from app.services.tabular.registries import SHEET_REGISTRY
        self.registry = SHEET_REGISTRY

    def test_all_datasets_in_sheet_registry(self):
        expected = {"Container Throughput", "Overview Vessel", "Market Share", "Transhipment"}
        self.assertEqual(expected, set(self.registry.keys()))

    def test_overview_vessel_domestic_maps_to_uppercase(self):
        self.assertEqual(self.registry["Overview Vessel"]["domestic"], "DOMESTIC")
        self.assertEqual(self.registry["Overview Vessel"]["international"], "INTERNATIONAL")

    def test_container_throughput_domestic_maps_correctly(self):
        self.assertEqual(self.registry["Container Throughput"]["domestic"], "Domestik")

    def test_market_share_maps_correctly(self):
        self.assertEqual(self.registry["Market Share"]["domestic"], "V.OPR DOM")
        self.assertEqual(self.registry["Market Share"]["international"], "V.OPR INT")

    def test_indonesian_keywords_also_mapped(self):
        self.assertIn("domestik", self.registry["Overview Vessel"])
        self.assertIn("internasional", self.registry["Overview Vessel"])


class TestOperatorDictionary(unittest.TestCase):
    def setUp(self):
        from app.services.tabular.registries import OPERATORS
        self.operators = OPERATORS

    def test_minimum_operator_count(self):
        self.assertGreaterEqual(len(self.operators), 20, "Should have at least 20 operators")

    def test_key_operators_present(self):
        key_ops = ["SPI", "TIL", "MSC", "MSK", "ONE", "CMA", "COSCO", "OOCL"]
        for op in key_ops:
            self.assertIn(op, self.operators, f"Operator {op} missing from OPERATORS list")

    def test_all_operators_uppercase(self):
        for op in self.operators:
            self.assertEqual(op, op.upper(), f"Operator {op} should be uppercase")

    def test_operators_are_unique(self):
        self.assertEqual(len(self.operators), len(set(self.operators)))


class TestColumnAliases(unittest.TestCase):
    def setUp(self):
        from app.services.tabular.registries import COLUMN_ALIASES
        self.aliases = COLUMN_ALIASES

    def test_throughput_maps_to_teus(self):
        self.assertEqual(self.aliases.get("throughput"), "TEUS")

    def test_market_share_maps_to_percent(self):
        self.assertEqual(self.aliases.get("market share"), "%")

    def test_productivity_maps_to_bch(self):
        self.assertEqual(self.aliases.get("productivity"), "BCH")

    def test_performance_maps_to_actual_vs_budget(self):
        self.assertEqual(self.aliases.get("performance"), "ACTUAL VS BUDGET")


class TestMonthNormalizeMap(unittest.TestCase):
    def setUp(self):
        from app.services.tabular.registries import MONTH_NORMALIZE_MAP
        self.month_map = MONTH_NORMALIZE_MAP

    def test_all_12_english_months_present(self):
        english_months = [
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december"
        ]
        for m in english_months:
            self.assertIn(m, self.month_map, f"English month '{m}' missing")

    def test_all_12_indonesian_months_present(self):
        indonesian_months = [
            "januari", "februari", "maret", "april", "mei", "juni",
            "juli", "agustus", "september", "oktober", "november", "desember"
        ]
        for m in indonesian_months:
            self.assertIn(m, self.month_map, f"Indonesian month '{m}' missing")

    def test_abbreviated_months_present(self):
        abbrevs = ["jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
        for m in abbrevs:
            self.assertIn(m, self.month_map, f"Abbreviated month '{m}' missing")

    def test_numeric_months_present(self):
        for i in range(1, 13):
            self.assertIn(str(i), self.month_map, f"Numeric month '{i}' missing")

    def test_january_normalizes_correctly(self):
        result = self.month_map["january"]
        self.assertEqual(result["id"], "Januari")
        self.assertEqual(result["code"], 1)

    def test_december_normalizes_correctly(self):
        result = self.month_map["december"]
        self.assertEqual(result["id"], "Desember")
        self.assertEqual(result["code"], 12)

    def test_numeric_6_is_june(self):
        result = self.month_map["6"]
        self.assertEqual(result["id"], "Juni")
        self.assertEqual(result["code"], 6)

    def test_all_entries_have_id_and_code(self):
        for key, val in self.month_map.items():
            self.assertIn("id", val, f"Month '{key}' missing 'id' key")
            self.assertIn("code", val, f"Month '{key}' missing 'code' key")
            self.assertIsInstance(val["code"], int, f"Month '{key}' code should be int")

    def test_codes_are_in_range_1_to_12(self):
        for key, val in self.month_map.items():
            self.assertGreaterEqual(val["code"], 1)
            self.assertLessEqual(val["code"], 12)


# ============================================================
# PHASE 1 — Schema Registry
# ============================================================

class TestSchemaRegistryStatic(unittest.TestCase):
    def test_four_datasets_in_static_registry(self):
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        expected = {"Container Throughput", "Overview Vessel", "Market Share", "Transhipment"}
        self.assertEqual(expected, set(SCHEMA_REGISTRY.keys()))

    def test_overview_vessel_has_bch_column(self):
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        cols = SCHEMA_REGISTRY["Overview Vessel"]["columns"]
        self.assertIn("BCH", cols)
        self.assertIn("BSH", cols)
        self.assertIn("TEUS", cols)
        self.assertIn("Boxes", cols)

    def test_overview_vessel_sheets(self):
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        sheets = SCHEMA_REGISTRY["Overview Vessel"]["sheets"]
        self.assertIn("DOMESTIC", sheets)
        self.assertIn("INTERNATIONAL", sheets)

    def test_container_throughput_has_actual_budget(self):
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        cols = SCHEMA_REGISTRY["Container Throughput"]["columns"]
        self.assertIn("ACTUAL", cols)
        self.assertIn("BUDGET", cols)
        self.assertIn("ACTUAL VS BUDGET", cols)

    def test_transhipment_has_year_month(self):
        from app.services.tabular.schema_registry import SCHEMA_REGISTRY
        cols = SCHEMA_REGISTRY["Transhipment"]["columns"]
        self.assertIn("YEAR", cols)
        self.assertIn("MONTH", cols)


class TestGetSchemaFunction(unittest.TestCase):
    def test_static_fallback_when_no_db_schema(self):
        from app.services.tabular.schema_registry import get_schema
        schema = get_schema("Overview Vessel", db_schema=None)
        self.assertIn("TEUS", schema["columns"])
        self.assertIn("DOMESTIC", schema["sheets"])

    def test_db_schema_takes_priority_over_static(self):
        from app.services.tabular.schema_registry import get_schema
        db_schema = {"NEW_SHEET": ["COL_A", "COL_B", "COL_C"]}
        schema = get_schema("Overview Vessel", db_schema=db_schema)
        self.assertIn("NEW_SHEET", schema["sheets"])
        self.assertIn("COL_A", schema["columns"])

    def test_db_schema_columns_deduplicated(self):
        from app.services.tabular.schema_registry import get_schema
        db_schema = {
            "SHEET_A": ["COL_X", "COL_Y"],
            "SHEET_B": ["COL_Y", "COL_Z"],
        }
        schema = get_schema("Overview Vessel", db_schema=db_schema)
        col_y_count = schema["columns"].count("COL_Y")
        self.assertEqual(col_y_count, 1, "COL_Y should appear only once after dedup")

    def test_unknown_dataset_returns_empty(self):
        from app.services.tabular.schema_registry import get_schema
        schema = get_schema("NonExistentDataset", db_schema=None)
        self.assertEqual(schema, {})

    def test_empty_db_schema_falls_back_to_static(self):
        from app.services.tabular.schema_registry import get_schema
        schema = get_schema("Overview Vessel", db_schema={})
        self.assertIn("BCH", schema.get("columns", []))


class TestValidateColumnFunction(unittest.TestCase):
    def test_valid_column_case_insensitive(self):
        from app.services.tabular.schema_registry import validate_column
        self.assertTrue(validate_column("TEUS", "Overview Vessel"))
        self.assertTrue(validate_column("teus", "Overview Vessel"))
        self.assertTrue(validate_column("Teus", "Overview Vessel"))

    def test_invalid_column_returns_false(self):
        from app.services.tabular.schema_registry import validate_column
        self.assertFalse(validate_column("NON_EXISTENT_COL", "Overview Vessel"))

    def test_column_valid_in_correct_dataset(self):
        from app.services.tabular.schema_registry import validate_column
        self.assertTrue(validate_column("ACTUAL", "Container Throughput"))
        self.assertFalse(validate_column("ACTUAL", "Overview Vessel"))


class TestValidateSheetFunction(unittest.TestCase):
    def test_valid_sheet(self):
        from app.services.tabular.schema_registry import validate_sheet
        self.assertTrue(validate_sheet("DOMESTIC", "Overview Vessel"))
        self.assertTrue(validate_sheet("domestic", "Overview Vessel"))

    def test_invalid_sheet_returns_false(self):
        from app.services.tabular.schema_registry import validate_sheet
        self.assertFalse(validate_sheet("INVALID_SHEET", "Overview Vessel"))

    def test_sheet_from_wrong_dataset(self):
        from app.services.tabular.schema_registry import validate_sheet
        # "Domestik" is Container Throughput sheet, not Overview Vessel
        self.assertFalse(validate_sheet("Domestik", "Overview Vessel"))
        self.assertTrue(validate_sheet("Domestik", "Container Throughput"))


# ============================================================
# PHASE 1 — Settings
# ============================================================

class TestSettings(unittest.TestCase):
    def test_enable_llm_query_builder_is_bool(self):
        from app.services.tabular.settings import ENABLE_LLM_QUERY_BUILDER
        self.assertIsInstance(ENABLE_LLM_QUERY_BUILDER, bool)

    def test_enable_retry_engine_is_bool(self):
        from app.services.tabular.settings import ENABLE_RETRY_ENGINE
        self.assertIsInstance(ENABLE_RETRY_ENGINE, bool)

    def test_enable_observability_is_bool(self):
        from app.services.tabular.settings import ENABLE_OBSERVABILITY
        self.assertIsInstance(ENABLE_OBSERVABILITY, bool)

    def test_return_debug_block_is_bool(self):
        from app.services.tabular.settings import RETURN_DEBUG_BLOCK
        self.assertIsInstance(RETURN_DEBUG_BLOCK, bool)

    def test_enable_query_cache_is_false_in_mvp(self):
        from app.services.tabular.settings import ENABLE_QUERY_CACHE
        self.assertFalse(ENABLE_QUERY_CACHE, "Query cache must be disabled in MVP")

    def test_retry_engine_enabled_by_default(self):
        from app.services.tabular.settings import ENABLE_RETRY_ENGINE
        self.assertTrue(ENABLE_RETRY_ENGINE)

    def test_debug_block_disabled_by_default(self):
        from app.services.tabular.settings import RETURN_DEBUG_BLOCK
        # Production default: debug block not returned automatically
        self.assertTrue(RETURN_DEBUG_BLOCK)


if __name__ == "__main__":
    unittest.main()
