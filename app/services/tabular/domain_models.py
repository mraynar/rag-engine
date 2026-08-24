"""
Domain models for tabular query planning.

Contains enums and dataclasses representing the query planning pipeline.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ============================================================
# ENUMS
# ============================================================

class QueryType(Enum):
    """Type of query operation required."""
    SIMPLE = "simple"
    AGGREGATION = "aggregation"
    COMPARISON = "comparison"
    RANKING = "ranking"
    TREND = "trend"
    MULTI_HOP = "multi_hop"


class UserIntent(Enum):
    """Fine-grained user intent within a query type."""
    VALUE_LOOKUP = "value_lookup"
    TOP_N = "top_n"
    BOTTOM_N = "bottom_n"
    COMPARISON = "comparison"
    TREND_ANALYSIS = "trend_analysis"
    TOTAL_AGGREGATION = "total_aggregation"
    PERCENTAGE_LOOKUP = "percentage_lookup"
    MULTI_HOP = "multi_hop"


class BuildMethod(Enum):
    """Method used to build the query plan."""
    DETERMINISTIC = "deterministic"
    LLM_FALLBACK = "llm_fallback"


class ResultQuality(Enum):
    """Quality assessment of execution result."""
    VALID = "valid"
    EMPTY = "empty"
    NAN = "nan"
    ALL_ZERO = "all_zero"


class RetryStrategy(Enum):
    """Retry strategies for failed query execution."""
    MONTH_RETRY = "month_retry"
    SHEET_RETRY = "sheet_retry"
    COLUMN_RETRY = "column_retry"
    OPERATOR_RETRY = "operator_retry"
    RELAXED_FILTER_RETRY = "relaxed_filter_retry"
    AGGREGATION_RETRY = "aggregation_retry"


class FilterOperator(Enum):
    """Filter operators matching pandas syntax."""
    EQ = "=="
    NEQ = "!="
    GT = ">"
    LT = "<"
    GTE = ">="
    LTE = "<="
    CONTAINS = "contains"
    IN = "in"


class RoutingMethod(Enum):
    """Method used to route to a dataset."""
    EXPLICIT_PARAM = "explicit_param"
    AMBIGUOUS = "ambiguous"


# ============================================================
# DATACLASSES
# ============================================================

@dataclass
class FilterCondition:
    """A single filter condition for query execution."""
    column: str
    operator: FilterOperator
    value: Any


@dataclass
class AggregationSpec:
    """Specification for aggregation operation."""
    func: str
    column: Optional[str] = None


@dataclass
class MonthContext:
    """Normalized month reference."""
    month_str: str
    month_code: int
    year: int


@dataclass
class QueryAST:
    """Abstract syntax tree representing the parsed question."""
    query_type: QueryType
    intent: UserIntent
    filters: list = field(default_factory=list)
    aggregation: Optional[AggregationSpec] = None
    build_method: BuildMethod = BuildMethod.DETERMINISTIC


@dataclass
class QueryPlan:
    """Fully resolved execution plan for query."""
    sheet: Optional[str]
    filters: list
    aggregation: Optional[AggregationSpec]
    group_by: Optional[list]
    sort: Optional[str]
    limit: Optional[int]
    build_method: BuildMethod


@dataclass
class DatasetRouteResult:
    """Result of dataset routing."""
    dataset: str
    method: RoutingMethod
    candidates: list = field(default_factory=list)
    score: float = 0.0


@dataclass
class ResolvedEntities:
    """Entities extracted from the question."""
    operators: list = field(default_factory=list)
    metrics: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    month: Optional[MonthContext] = None


@dataclass
class SubQuery:
    """A decomposed step of a multi-hop question."""
    step: int
    question: str
    template_type: QueryType = QueryType.SIMPLE
    depends_on: Optional[int] = None


@dataclass
class ExecutionResult:
    """Raw pandas output with quality assessment."""
    data: Any
    quality: ResultQuality
    row_count: int
    retry_count: int = 0
    last_retry_strategy: Optional[RetryStrategy] = None
