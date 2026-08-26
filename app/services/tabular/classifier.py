"""
Classifier: Semantic query classification logic.

Responsibilities:
- Classify QueryType (SIMPLE, AGGREGATION, RANKING, COMPARISON, TREND, MULTI_HOP)
- Determine UserIntent (VALUE_LOOKUP, TOP_N, BOTTOM_N, COMPARISON, TREND_ANALYSIS, TOTAL_AGGREGATION, PERCENTAGE_LOOKUP, MULTI_HOP)
- Construct safe filters from resolved entities (YEAR, MONTH, operator)
- Determine aggregation functions from keywords (tertinggi → max, terendah → min, total → sum)
- Mark queries as DETERMINISTIC or LLM_FALLBACK

Does NOT:
- Execute queries
- Call Gemini API
- Build QueryPlan
- Access database
- Perform pandas operations
"""
import re
from typing import Optional

from app.services.tabular.domain_models import (
    QueryAST,
    QueryType,
    UserIntent,
    BuildMethod,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    ResolvedEntities,
)
from app.services.tabular.schema_registry import get_schema


def classify_query(
    question: str,
    resolved: ResolvedEntities,
    dataset: Optional[str] = None,
) -> QueryAST:
    """
    Classify question into QueryAST using resolved entities.
    
    Args:
        question: User's natural language question
        resolved: Entities resolved by resolver (operators, metrics, columns, month)
        dataset: Dataset context for schema-aware classification
    
    Returns:
        QueryAST with query_type, intent, filters, aggregation, build_method
    """
    from app.services.tabular.resolver import sanitize_leading_number
    question = sanitize_leading_number(question)
    question_lower = question.lower()
    
    # Check if we have enough information for deterministic classification
    has_metrics = len(resolved.metrics) > 0 or len(resolved.columns) > 0
    has_temporal = resolved.month is not None and resolved.month.year > 0
    
    # If no entities resolved and question is vague, fall back to LLM
    if not has_metrics and not resolved.operators and not has_temporal:
        return _create_llm_fallback(question_lower, resolved)
    
    # Detect query patterns
    is_comparison = _is_comparison_query(question_lower)
    is_trend = _is_trend_query(question_lower)
    is_ranking_top = _is_ranking_top_query(question_lower)
    is_ranking_bottom = _is_ranking_bottom_query(question_lower)
    is_total = _is_total_aggregation_query(question_lower)
    is_percentage = _is_percentage_query(question_lower)
    
    # Determine query type and intent
    if is_comparison:
        query_type = QueryType.MULTI_HOP
        intent = UserIntent.MULTI_HOP
        aggregation = None
        build_method = BuildMethod.DETERMINISTIC
    elif is_trend:
        query_type = QueryType.TREND
        intent = UserIntent.TREND_ANALYSIS
        aggregation = None
        build_method = BuildMethod.DETERMINISTIC
    elif is_ranking_top:
        query_type = QueryType.RANKING
        intent = UserIntent.TOP_N
        aggregation = _create_aggregation_spec("max", resolved, question_lower)
        build_method = BuildMethod.DETERMINISTIC
    elif is_ranking_bottom:
        query_type = QueryType.RANKING
        intent = UserIntent.BOTTOM_N
        aggregation = _create_aggregation_spec("min", resolved, question_lower)
        build_method = BuildMethod.DETERMINISTIC
    elif is_total:
        query_type = QueryType.AGGREGATION
        intent = UserIntent.TOTAL_AGGREGATION
        is_transaksi = "transaksi" in question_lower or "jumlah transaksi" in question_lower or "banyak transaksi" in question_lower
        if is_transaksi:
            if dataset == "Transhipment":
                aggregation = AggregationSpec(func="count")
            else:
                col = None
                if resolved.columns:
                    col = resolved.columns[0]
                elif resolved.metrics:
                    col = resolved.metrics[0]
                if not col:
                    col = "TEUS"
                aggregation = AggregationSpec(func="sum", column=col)
        else:
            aggregation = _create_aggregation_spec("sum", resolved)
            if not aggregation and "jumlah" in question_lower:
                aggregation = AggregationSpec(func="count")
        build_method = BuildMethod.DETERMINISTIC
    elif is_percentage:
        if dataset == "Market Share":
            query_type = QueryType.SIMPLE
            intent = UserIntent.PERCENTAGE_LOOKUP
            aggregation = None
        else:
            query_type = QueryType.MULTI_HOP
            intent = UserIntent.MULTI_HOP
            aggregation = None
        build_method = BuildMethod.DETERMINISTIC
    else:
        # Default: simple value lookup
        query_type = QueryType.SIMPLE
        intent = UserIntent.VALUE_LOOKUP
        aggregation = None
        build_method = BuildMethod.DETERMINISTIC
    
    # Construct filters
    filters = _construct_filters(resolved, dataset)
    
    return QueryAST(
        query_type=query_type,
        intent=intent,
        filters=filters,
        aggregation=aggregation,
        build_method=build_method
    )


def _is_comparison_query(question_lower: str) -> bool:
    """Detect comparison/difference queries requiring multi-hop."""
    comparison_keywords = [
        "selisih",
        "perbedaan",
        "bandingkan",
        "dibanding",
        "versus",
        "vs",
        r"\bdan\b.*\bdan\b",  # Pattern: "2024 dan 2025"
    ]
    
    for keyword in comparison_keywords:
        if re.search(keyword, question_lower):
            return True
    
    return False


def _is_trend_query(question_lower: str) -> bool:
    """Detect trend analysis queries."""
    trend_keywords = [
        "tren",
        "trend",
        "perkembangan",
        "perubahan",
        "per bulan",
        "per tahun",
        "selama",
    ]
    
    return any(kw in question_lower for kw in trend_keywords)


def _is_ranking_top_query(question_lower: str) -> bool:
    """Detect ranking queries asking for highest/maximum/top."""
    top_keywords = [
        "tertinggi",
        "maksimal",
        "paling banyak",
        "paling tinggi",
        "terbanyak",
        "terbesar",
    ]
    
    return any(kw in question_lower for kw in top_keywords)


def _is_ranking_bottom_query(question_lower: str) -> bool:
    """Detect ranking queries asking for lowest/minimum/bottom."""
    bottom_keywords = [
        "terendah",
        "minimal",
        "paling sedikit",
        "paling rendah",
        "tersedikit",
        "terkecil",
    ]
    
    return any(kw in question_lower for kw in bottom_keywords)


def _is_total_aggregation_query(question_lower: str) -> bool:
    """Detect total/sum aggregation queries."""
    total_keywords = [
        "total",
        "jumlah",
        "keseluruhan",
        "semua",
    ]
    
    return any(kw in question_lower for kw in total_keywords)


def _is_percentage_query(question_lower: str) -> bool:
    """Detect percentage/market share queries."""
    percentage_keywords = [
        "persentase",
        "persen",
        "market share",
        "pangsa pasar",
        "%",
    ]
    
    return any(kw in question_lower for kw in percentage_keywords)


def _create_aggregation_spec(
    func: str,
    resolved: ResolvedEntities,
    question_lower: Optional[str] = None
) -> Optional[AggregationSpec]:
    """
    Create aggregation spec from function and resolved metrics.
    
    Args:
        func: Aggregation function (sum, max, min, mean, count)
        resolved: ResolvedEntities containing metrics/columns
        question_lower: Optional lowercased question for context-aware ranking
    
    Returns:
        AggregationSpec or None if no valid column
    """
    # Pick first metric/column as aggregation target, filtering out categorical grouping dimensions
    column = None
    target_columns = []
    if resolved.columns:
        target_columns.extend(resolved.columns)
    if resolved.metrics:
        target_columns.extend(resolved.metrics)
        
    for col in target_columns:
        if col.upper() not in ["VESSEL OPERATOR", "LOP", "OPERATOR", "YEAR", "MONTH", "BULAN", "_SHEET"]:
            column = col
            break
    
    if column:
        # Quantity ranking semantics: use sum instead of max/min for operator/entity queries
        if func in ["max", "min"] and column.upper() in ["TEUS", "BOXES", "20'", "40'", "ACTUAL", "BUDGET"]:
            if question_lower:
                is_operator_query = any(w in question_lower for w in ["operator", "vessel operator", "pelayaran", "pemilik kapal", "lop"])
                if is_operator_query:
                    return AggregationSpec(func="sum", column=column)
        return AggregationSpec(func=func, column=column)
    
    return None


def _construct_filters(
    resolved: ResolvedEntities,
    dataset: Optional[str] = None
) -> list:
    """
    Construct filter conditions from resolved entities.
    
    Args:
        resolved: ResolvedEntities with operators, month, etc.
        dataset: Dataset name for schema-aware operator column detection
    
    Returns:
        List of FilterCondition objects
    """
    filters = []
    
    # Year filter
    if resolved.month and resolved.month.year > 0:
        filters.append(FilterCondition(
            column="YEAR",
            operator=FilterOperator.EQ,
            value=resolved.month.year
        ))
    
    # Month filter
    if resolved.month and resolved.month.month_code > 0:
        filters.append(FilterCondition(
            column="MONTH",
            operator=FilterOperator.EQ,
            value=resolved.month.month_str
        ))
    
    # Operator filter (dataset-aware column detection)
    if resolved.operators:
        operator_column = _get_operator_column(dataset)
        
        if len(resolved.operators) == 1:
            # Single operator: use EQ
            filters.append(FilterCondition(
                column=operator_column,
                operator=FilterOperator.EQ,
                value=resolved.operators[0]
            ))
        else:
            # Multiple operators: use IN
            filters.append(FilterCondition(
                column=operator_column,
                operator=FilterOperator.IN,
                value=resolved.operators
            ))
    
    return filters


def _get_operator_column(dataset: Optional[str]) -> str:
    """
    Determine the operator column name based on dataset.
    
    Different datasets use different column names:
    - Overview Vessel: LOP
    - Market Share: LOP
    - Transhipment: VESSEL OPERATOR
    - Container Throughput: No operator column (return LOP as default)
    
    Args:
        dataset: Dataset name
    
    Returns:
        Column name for operator dimension (default: "LOP")
    """
    if not dataset:
        return "LOP"  # Default
    
    # Get schema to check available columns
    schema = get_schema(dataset, db_schema=None)
    columns = schema.get("columns", [])
    
    # Smart operator column search with dataset-specific priority
    if dataset == "Transhipment":
        targets = ["vessel operator", "operator", "lop", "v.opr"]
    elif dataset in ["Market Share", "Overview Vessel"]:
        targets = ["lop", "operator", "vessel operator", "v.opr"]
    else:
        targets = ["lop", "vessel operator", "operator", "v.opr"]

    for target in targets:
        for col in columns:
            if col.lower() == target:
                return col
                
    for target in targets:
        for col in columns:
            if target in col.lower():
                return col
    
    # Default fallback
    return "LOP"


def _create_llm_fallback(
    question_lower: str,
    resolved: ResolvedEntities
) -> QueryAST:
    """
    Create QueryAST marked for LLM fallback.
    
    Used when deterministic classification cannot safely determine query semantics.
    
    Args:
        question_lower: Lowercased question
        resolved: ResolvedEntities (may be empty)
    
    Returns:
        QueryAST with LLM_FALLBACK build method
    """
    # Minimal filters from resolved entities
    filters = []
    if resolved.month and resolved.month.year > 0:
        filters.append(FilterCondition(
            column="YEAR",
            operator=FilterOperator.EQ,
            value=resolved.month.year
        ))
    
    return QueryAST(
        query_type=QueryType.SIMPLE,  # Conservative default
        intent=UserIntent.VALUE_LOOKUP,
        filters=filters,
        aggregation=None,
        build_method=BuildMethod.LLM_FALLBACK
    )
