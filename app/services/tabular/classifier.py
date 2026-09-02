"""
Klasifikasi semantik pertanyaan menjadi QueryAST (tipe query, intent, filter, dan agregasi).
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
            aggregation = _create_aggregation_spec("sum", resolved, question_lower)
            if not aggregation:
                # Determine default numeric column by dataset
                default_col = None
                if dataset == "Komersial Dashboard":
                    default_col = "TOTAL ALL REVENUE"
                elif dataset == "RestNDisc":
                    default_col = "NOMINAL PERSETUJUAN KERINGANAN"
                elif dataset in ["Overview Vessel", "Container Throughput", "Overview Box"]:
                    default_col = "TEUS"
                elif dataset == "Vessel Service":
                    default_col = "TOTAL CALL"
                elif dataset == "Realisasi UC":
                    default_col = "TOTAL TEUS"
                elif dataset == "Transhipment":
                    default_col = "VESSEL REVENUE"

                if default_col:
                    aggregation = AggregationSpec(func="sum", column=default_col)
                elif "jumlah" in question_lower and any(w in question_lower for w in ["transaksi", "permohonan", "panggilan"]):
                    aggregation = AggregationSpec(func="count")
                else:
                    aggregation = AggregationSpec(func="sum", column="TEUS")
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
        "berbeda",
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
        "10 besar",
        "top ",
        "teratas",
        "paling tinggi",
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
    # Pick first valid metric column as aggregation target (metrics priority over columns)
    column = None
    target_columns = []
    if resolved.metrics:
        target_columns.extend(resolved.metrics)
    if resolved.columns:
        target_columns.extend(resolved.columns)
        
    excluded_cols = {
        "VESSEL OPERATOR", "LOP", "OPERATOR", "NAMA PERUSAHAAN", "CUSTOMER",
        "YEAR", "TAHUN", "_YEAR", "MONTH", "BULAN", "MONTH_CODE", "_MONTH_CODE", "_MONTH_EN",
        "DATE", "TANGGAL", "TIMESTAMP", "_SHEET", "_OPERATOR", "KATEGORI", "STATUS", "SERVICE", "ROUTES"
    }
    for col in target_columns:
        if col.upper().strip() not in excluded_cols:
            column = col
            break
    
    if column:
        # Quantity & Revenue ranking semantics: use sum instead of max/min for operator/entity queries
        volume_revenue_cols = {
            "TEUS", "BOXES", "20'", "40'", "ACTUAL", "BUDGET",
            "TOTAL ALL REVENUE", "VESSEL REVENUE", "REVENUE", "TOTAL REVENUE",
            "TOTAL BOX", "TOTAL TEUS"
        }
        if func in ["max", "min"] and column.upper().strip() in volume_revenue_cols:
            if question_lower:
                is_operator_query = any(w in question_lower for w in ["operator", "vessel operator", "pelayaran", "pemilik kapal", "lop", "line operator"])
                if is_operator_query:
                    return AggregationSpec(func="sum", column=column)
        
        # Overrides: % should use mean instead of sum
        if (
            column == "%"
            and question_lower
            and "market share" in question_lower
            and re.search(r"\b\d+\s*(?:besar|teratas|tertinggi)\b", question_lower)
        ):
            if func in ["max", "min", "sum"]:
                func = "mean"
            
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
    
    # Month filter - use BULAN for datasets storing month in Indonesian BULAN column
    if resolved.month and resolved.month.month_code > 0:
        # Datasets that use BULAN (Indonesian name) instead of MONTH
        bulan_datasets = {"Komersial Dashboard", "Realisasi UC"}
        month_col = "BULAN" if dataset in bulan_datasets else "MONTH"
        filters.append(FilterCondition(
            column=month_col,
            operator=FilterOperator.EQ,
            value=resolved.month.month_str  # e.g. "Maret" - executor will match against stored values
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
    
    # Transhipment KATEGORI filter for loading/discharge
    if dataset == "Transhipment":
        question_lower_ctx = resolved.month.month_str if resolved.month else ""
        # We need the question here — use a module-level check pattern
        # This is passed in via dataset context; filter by KATEGORI if keywords found
        pass  # KATEGORI filter is applied in tabular_query.py based on question keywords
    
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
