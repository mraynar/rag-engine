"""
Query Builder: Deterministic QueryPlan construction.

Responsibilities:
- Convert QueryAST + Template + ResolvedEntities + Schema → QueryPlan
- Resolve abstract dimensions to physical columns
- Validate all columns against schema
- Preserve entities through SubQuery decomposition
- Handle multi-hop query plan building

Does NOT:
- Execute queries
- Access database
- Perform pandas operations
- Calculate final answers
"""
import re
from typing import Optional, List, Dict, Any

from app.services.tabular.domain_models import (
    QueryAST,
    QueryPlan,
    QueryType,
    UserIntent,
    BuildMethod,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    ResolvedEntities,
    SubQuery,
)
from app.services.tabular.schema_registry import get_schema, validate_column
from app.services.tabular.query_templates import get_template, get_grouping_dimension_column


class QueryBuildError(Exception):
    """Raised when QueryPlan cannot be built deterministically"""
    pass


def build_query_plan(
    ast: QueryAST,
    question: str,
    resolved: ResolvedEntities,
    dataset: str,
    schema: Optional[Dict] = None,
    subquery: Optional[SubQuery] = None,
) -> QueryPlan:
    """
    Build QueryPlan from QueryAST, template, and resolved entities.
    
    CRITICAL: Preserves original entities even when building from SubQuery.
    
    Args:
        ast: Classified QueryAST
        question: Question text (original or SubQuery-synthesized)
        resolved: Original resolved entities (MUST be preserved)
        dataset: Dataset name for schema validation
        schema: Optional DB schema (if None, uses static registry)
        subquery: Optional SubQuery context (for multi-hop)
    
    Returns:
        QueryPlan with validated columns and complete filters
    
    Raises:
        QueryBuildError: When plan cannot be built deterministically
    """
    from app.services.tabular.resolver import sanitize_leading_number
    question = sanitize_leading_number(question)
    # Get template for this query type/intent
    template = get_template(ast.query_type, ast.intent)
    
    # Get schema for validation
    db_schema = schema or get_schema(dataset, db_schema=None)
    
    # Helper to resolve readable metric names
    def get_metric_label(col: str) -> str:
        return "market share" if col == "%" else col

    # Validate resolved metrics
    if resolved.metrics:
        for m in resolved.metrics:
            if not validate_column(m, dataset, db_schema=db_schema):
                raise QueryBuildError(
                    f"Metric '{get_metric_label(m)}' tidak tersedia pada dataset '{dataset}'"
                )
    
    # Build filters (preserving AST filters + inherited entities)
    filters = _build_filters(ast, resolved, dataset, db_schema, question)
    
    aggregation = _build_aggregation(ast, template, resolved, dataset, db_schema, question)
    
    # Build group_by
    group_by = _build_group_by(ast, template, resolved, dataset, db_schema, question)
    
    # Build sort and limit
    sort, limit = _build_sort_and_limit(template, ast, question)
    
    # Validate plan before returning
    _validate_plan(filters, aggregation, group_by, dataset, db_schema)
    
    return QueryPlan(
        sheet=None,  # Sheet routing handled separately by executor
        filters=filters,
        aggregation=aggregation,
        group_by=group_by,
        sort=sort,
        limit=limit,
        build_method=ast.build_method
    )


def _build_filters(
    ast: QueryAST,
    resolved: ResolvedEntities,
    dataset: str,
    schema: Dict,
    question: str
) -> List[FilterCondition]:
    """
    Build complete filter list from AST + inherited entities.
    
    CRITICAL: Preserves operator filters from original query.
    
    Args:
        ast: QueryAST with existing filters
        resolved: Original ResolvedEntities (operators/month preserved)
        dataset: Dataset name
        schema: Schema for validation
        question: Question text
    
    Returns:
        List of FilterCondition objects
    """
    filters = []
    
    # Start with AST filters (already validated by classifier)
    filters.extend(ast.filters)
    
    # Transhipment-specific dimension filters
    if dataset == "Transhipment":
        question_lower = question.lower()
        resolved_schema = get_schema(dataset, db_schema=schema)
        columns = resolved_schema.get("columns", [])
        
        # Match DIRECT OR CY TRANS column
        direct_col = next((c for c in columns if c.lower() in ["direct or cy trans", "direct or cy"]), None)
        if direct_col:
            if not any(f.column == direct_col for f in filters):
                if "direct" in question_lower:
                    filters.append(FilterCondition(column=direct_col, operator=FilterOperator.EQ, value="Direct"))
                elif "cy" in question_lower:
                    filters.append(FilterCondition(column=direct_col, operator=FilterOperator.EQ, value="CY"))
                    
        # Match LOADING TERMINAL column
        load_col = next((c for c in columns if c.lower() == "loading terminal"), None)
        if load_col:
            if not any(f.column == load_col for f in filters):
                if "ttl" in question_lower:
                    filters.append(FilterCondition(column=load_col, operator=FilterOperator.EQ, value="TTL"))
    
    # Add operator filter if operators resolved (and not already in AST)
    if resolved.operators:
        # Check if operator filter already exists in AST
        operator_column = _resolve_operator_column(dataset, schema)
        existing_op_filters = [f for f in filters if f.column == operator_column]
        
        if not existing_op_filters:
            # Add operator filter
            if len(resolved.operators) == 1:
                filters.append(FilterCondition(
                    column=operator_column,
                    operator=FilterOperator.EQ,
                    value=resolved.operators[0]
                ))
            else:
                filters.append(FilterCondition(
                    column=operator_column,
                    operator=FilterOperator.IN,
                    value=resolved.operators
                ))
    
    return filters


def _build_aggregation(
    ast: QueryAST,
    template: Dict[str, Any],
    resolved: ResolvedEntities,
    dataset: str,
    schema: Dict,
    question: str
) -> Optional[AggregationSpec]:
    """
    Build aggregation spec from AST or template defaults.
    """
    # Helper to resolve readable metric names
    def get_metric_label(col: str) -> str:
        return "market share" if col == "%" else col

    # If AST already has aggregation, use it
    if ast.aggregation:
        # Validate aggregation column
        if not validate_column(ast.aggregation.column, dataset, db_schema=schema):
            raise QueryBuildError(
                f"Metric '{get_metric_label(ast.aggregation.column)}' tidak tersedia pada dataset '{dataset}'"
            )
        return ast.aggregation
    
    # If template requires aggregation but AST doesn't have it, build from template
    if template.get("requires_aggregation"):
        agg_func = template.get("default_agg_func", "sum")
        
        # Get column from resolved entities (excluding categorical grouping dimensions)
        column = None
        candidates = []
        if resolved.columns:
            candidates.extend(resolved.columns)
        if resolved.metrics:
            candidates.extend(resolved.metrics)
            
        for col in candidates:
            if col.upper() not in ["VESSEL OPERATOR", "LOP", "OPERATOR", "YEAR", "MONTH", "BULAN", "_SHEET"]:
                column = col
                break
        
        if column:
            # Validate column
            if not validate_column(column, dataset, db_schema=schema):
                raise QueryBuildError(
                    f"Metric '{get_metric_label(column)}' tidak tersedia pada dataset '{dataset}'"
                )
            # Overrides: % should use mean instead of sum
            agg_func = "mean" if column == "%" else agg_func
            return AggregationSpec(func=agg_func, column=column)
        elif dataset == "Transhipment":
            raise QueryBuildError(
                "Aggregation column not found in dataset 'Transhipment'"
            )
    
    if ast.query_type in [QueryType.COMPARISON, QueryType.MULTI_HOP]:
        question_lower = question.lower()
        if any(w in question_lower for w in ["domestic", "domestik", "international", "internasional"]):
            column = None
            candidates = []
            if resolved.columns:
                candidates.extend(resolved.columns)
            if resolved.metrics:
                candidates.extend(resolved.metrics)
                
            for col in candidates:
                if col.upper() not in ["VESSEL OPERATOR", "LOP", "OPERATOR", "YEAR", "MONTH", "BULAN", "_SHEET"]:
                    column = col
                    break
                    
            if column:
                if not validate_column(column, dataset, db_schema=schema):
                    raise QueryBuildError(
                        f"Metric '{get_metric_label(column)}' tidak tersedia pada dataset '{dataset}'"
                    )
                func = "mean" if column == "%" else "sum"
                return AggregationSpec(func=func, column=column)
        elif len(resolved.operators) >= 2 or any(op.lower() in question_lower for op in resolved.operators):
            column = None
            candidates = []
            if resolved.columns:
                candidates.extend(resolved.columns)
            if resolved.metrics:
                candidates.extend(resolved.metrics)
                
            for col in candidates:
                if col.upper() not in ["VESSEL OPERATOR", "LOP", "OPERATOR", "YEAR", "MONTH", "BULAN", "_SHEET"]:
                    column = col
                    break
                    
            if column:
                if not validate_column(column, dataset, db_schema=schema):
                    raise QueryBuildError(
                        f"Metric '{get_metric_label(column)}' tidak tersedia pada dataset '{dataset}'"
                    )
                func = "mean" if column == "%" else "sum"
                return AggregationSpec(func=func, column=column)

    return None


def _build_group_by(
    ast: QueryAST,
    template: Dict[str, Any],
    resolved: ResolvedEntities,
    dataset: str,
    schema: Dict,
    question: str
) -> Optional[List[str]]:
    """
    Build GROUP BY columns from template grouping dimensions.
    
    Args:
        ast: QueryAST
        template: Query template
        resolved: ResolvedEntities
        dataset: Dataset name
        schema: Schema for validation
        question: Question text for keyword detection
    
    Returns:
        List of column names or None
    
    Raises:
        QueryBuildError: If grouping column invalid
    """
    if not template.get("requires_grouping"):
        if ast.query_type in [QueryType.COMPARISON, QueryType.MULTI_HOP]:
            question_lower = question.lower()
            if any(w in question_lower for w in ["domestic", "domestik", "international", "internasional"]):
                return ["_sheet"]
            if len(resolved.operators) >= 2 or any(op.lower() in question_lower for op in resolved.operators):
                op_col = _resolve_operator_column(dataset, schema)
                if validate_column(op_col, dataset, db_schema=schema):
                    return [op_col]
        return None
    
    # Resolve abstract grouping dimension from template
    grouping_dimension = template.get("grouping_dimension")

    # Dynamic grouping dimension override:
    question_lower = question.lower()
    columns = schema.get("columns", [])

    if "status mana" in question_lower or "berdasarkan status" in question_lower or "per status" in question_lower:
        status_col = next((c for c in columns if c.upper() == "STATUS"), None)
        if status_col:
            return [status_col]

    if "service mana" in question_lower or "berdasarkan service" in question_lower or "per service" in question_lower or "routes" in question_lower:
        service_col = next((c for c in columns if c.upper() in ["SERVICE", "ROUTES"]), None)
        if service_col:
            return [service_col]

    if "aktivitas" in question_lower or "kegiatan" in question_lower:
        act_col = next((c for c in columns if c.upper() in ["AKTIVITAS", "KEGIATAN", "ACTIVITY"]), None)
        if act_col:
            return [act_col]

    if "perusahaan mana" in question_lower or "perusahaan apa" in question_lower:
        comp_col = next((c for c in columns if "perusahaan" in c.lower() or "customer" in c.lower()), None)
        if comp_col:
            return [comp_col]

    # "masing-masing" / "setiap" / "per operator" detection
    if "masing-masing" in question_lower or "setiap" in question_lower or "per " in question_lower:
        if "vessel operator" in question_lower or "operator" in question_lower or "pelayaran" in question_lower:
            op_col = _resolve_operator_column(dataset, schema)
            if op_col and validate_column(op_col, dataset, db_schema=schema):
                return [op_col]

    # Dynamic grouping dimension override:
    # If the question asks "Tahun berapa..." or "Bulan apa...", we override grouping_dimension to "temporal"
    if "tahun berapa" in question.lower() or "bulan apa" in question.lower() or "bulan berapa" in question.lower() or "tren" in question.lower():
        grouping_dimension = "temporal"
    
    if not grouping_dimension:
        return None
    
    if grouping_dimension == "operator":
        # Resolve to physical operator column
        column = _resolve_operator_column(dataset, schema)
        
        # Validate column exists
        if not validate_column(column, dataset, db_schema=schema):
            raise QueryBuildError(
                f"Operator grouping column '{column}' not found in dataset '{dataset}'"
            )
        
        return [column]
    
    elif grouping_dimension == "temporal":
        # Resolve to MONTH or YEAR based on question keywords
        column = get_grouping_dimension_column("temporal", dataset, question)
        
        if column and validate_column(column, dataset, db_schema=schema):
            return [column]
        
        # Fallback to MONTH / BULAN if exists
        for m_name in ["MONTH", "BULAN"]:
            if validate_column(m_name, dataset, db_schema=schema):
                return [m_name]
        
        raise QueryBuildError(
            f"Temporal grouping column not found in dataset '{dataset}'"
        )
    
    return None


def _build_sort_and_limit(
    template: Dict[str, Any],
    ast: QueryAST,
    question: str = ""
) -> tuple:
    """
    Build sort and limit from template.
    """
    sort = template.get("sort_order")
    limit = template.get("default_limit")
    
    question_lower = question.lower()
    if any(w in question_lower for w in ["terbesar", "terbanyak", "tertinggi", "paling banyak", "maksimal"]):
        sort = "desc"
        limit = limit or 1
    elif any(w in question_lower for w in ["terkecil", "terendah", "tersedikit", "paling sedikit", "minimal"]):
        sort = "asc"
        limit = limit or 1

    if ast.query_type == QueryType.RANKING:
        match = re.search(r"\b(\d+)\s*(?:besar|teratas|tertinggi|terendah|terkecil)", question.lower())
        if match:
            limit = int(match.group(1))
    
    return sort, limit


def _resolve_operator_column(dataset: str, schema: Dict) -> str:
    """
    Resolve operator dimension to physical column name.
    """
    resolved_schema = get_schema(dataset, db_schema=schema)
    columns = resolved_schema.get("columns", [])
    
    # Smart operator column search with dataset-specific priority
    if dataset in ["Transhipment", "Vessel Service", "Komersial Dashboard", "Overview Box"]:
        targets = ["vessel operator", "operator", "lop", "v.opr", "customer", "shipping line"]
    elif dataset in ["RestNDisc"]:
        targets = ["nama perusahaan", "perusahaan", "customer"]
    elif dataset in ["Market Share", "Overview Vessel"]:
        targets = ["lop", "operator", "vessel operator", "v.opr"]
    else:
        targets = ["vessel operator", "lop", "operator", "nama perusahaan", "v.opr"]

    for target in targets:
        for col in columns:
            if col.lower() == target:
                return col
                
    for target in targets:
        for col in columns:
            if target in col.lower():
                return col
    
    for col in columns:
        if col.upper() in ["VESSEL OPERATOR", "LOP", "NAMA PERUSAHAAN", "CUSTOMER"]:
            return col

    return "VESSEL OPERATOR" if "VESSEL OPERATOR" in columns else "LOP"


def _validate_plan(
    filters: List[FilterCondition],
    aggregation: Optional[AggregationSpec],
    group_by: Optional[List[str]],
    dataset: str,
    schema: Dict
) -> None:
    """
    Validate QueryPlan columns against schema.
    
    Args:
        filters: List of filters
        aggregation: Aggregation spec
        group_by: Group by columns
        dataset: Dataset name
        schema: Schema dict
    
    Raises:
        QueryBuildError: If any column invalid
    """
    # Validate filter columns
    for f in filters:
        if not validate_column(f.column, dataset, db_schema=schema):
            raise QueryBuildError(
                f"Filter column '{f.column}' not found in dataset '{dataset}'"
            )
    
    # Aggregation already validated in _build_aggregation
    
    # Group by already validated in _build_group_by
