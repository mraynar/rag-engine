"""
Resolver: Deterministic entity resolution and routing logic.

Responsibilities:
- Route question to dataset (P1: explicit → P2: literal → P3: unique → P4: keywords → P5: ambiguous)
- Route to sheets within dataset
- Resolve entities (operators, metrics, columns, months, years)
- Normalize month references
- Resolve canonical column names from aliases

Does NOT determine:
- Aggregation functions (SUM/MAX/MIN/COUNT)
- Query intent (TOP_N/RANKING/COMPARISON)
- QueryAST or QueryPlan construction
"""
import re
from typing import Optional, List, Union

from app.services.tabular.domain_models import (
    DatasetRouteResult,
    RoutingMethod,
    ResolvedEntities,
    MonthContext,
)
from app.services.tabular.registries import (
    DATASET_REGISTRY,
    SHEET_REGISTRY,
    OPERATORS,
    COLUMN_ALIASES,
    MONTH_NORMALIZE_MAP,
)
from app.services.tabular.schema_registry import get_schema, validate_column


def sanitize_leading_number(q: str) -> str:
    if not q:
        return q
    match = re.match(r'^\s*(\d+)\s*([\.\)\-]?)\s+(\w+)', q)
    if match:
        num_str, separator, next_word = match.groups()
        next_word_lower = next_word.lower()
        query_starters = {
            "bagaimana", "berapa", "apakah", "siapa", "mana", "vessel", "operator",
            "tunjukkan", "tampilkan", "cari", "temukan", "hitung", "list", "daftar",
            "what", "how", "who", "which", "show", "find", "get", "coba", "tolong",
            "sebutkan", "jelaskan", "adakah"
        }
        if separator or next_word_lower in query_starters:
            word_idx = q.find(next_word)
            if word_idx != -1:
                return q[word_idx:]
    return q


def route_dataset(
    question: str,
    category_name: Optional[str] = None,
) -> DatasetRouteResult:
    """
    Route question to appropriate dataset using priority chain.
    
    Priority:
    P1: Explicit category_name parameter (always wins)
    P2: Literal dataset name in question
    P3: Unique entity match (not implemented - risky)
    P4: Weighted keyword scoring
    P5: Ambiguous (multiple candidates with similar scores)
    
    Args:
        question: User's natural language question
        category_name: Explicitly provided category/dataset name
    
    Returns:
        DatasetRouteResult with dataset, method, candidates, and score
    """
    question = sanitize_leading_number(question)
    question_lower = question.lower()
    
    # P1: Explicit category_name always wins
    if category_name and category_name in DATASET_REGISTRY:
        return DatasetRouteResult(
            dataset=category_name,
            method=RoutingMethod.EXPLICIT_PARAM,
            candidates=[],
            score=1.0
        )
    
    # P2: Literal dataset name in question
    for dataset_name in DATASET_REGISTRY.keys():
        if dataset_name.lower() in question_lower:
            return DatasetRouteResult(
                dataset=dataset_name,
                method=RoutingMethod.EXPLICIT_PARAM,  # Treating literal mention as explicit
                candidates=[],
                score=1.0
            )
    
    # P4: Weighted keyword scoring
    dataset_scores = {}
    for dataset_name, config in DATASET_REGISTRY.items():
        score = 0
        keywords = config.get("keywords", {})
        for keyword, weight in keywords.items():
            if keyword.lower() in question_lower:
                score += weight
        dataset_scores[dataset_name] = score
    
    # Find maximum score
    max_score = max(dataset_scores.values()) if dataset_scores else 0
    
    if max_score == 0:
        # P5: No evidence - ambiguous
        return DatasetRouteResult(
            dataset=list(DATASET_REGISTRY.keys())[0],  # Default to first dataset
            method=RoutingMethod.AMBIGUOUS,
            candidates=list(DATASET_REGISTRY.keys()),
            score=0.0
        )
    
    # Check if multiple datasets have similar high scores (ambiguity)
    top_datasets = [name for name, score in dataset_scores.items() if score == max_score]
    
    if len(top_datasets) > 1:
        # P5: Ambiguous - multiple datasets with equal evidence
        return DatasetRouteResult(
            dataset=top_datasets[0],  # Pick first as default
            method=RoutingMethod.AMBIGUOUS,
            candidates=top_datasets,
            score=max_score
        )
    
    # Single winner
    winner = top_datasets[0]
    return DatasetRouteResult(
        dataset=winner,
        method=RoutingMethod.EXPLICIT_PARAM,  # Using EXPLICIT_PARAM for keyword match
        candidates=[],
        score=max_score
    )


def route_sheet(
    question: str,
    dataset: str,
) -> Optional[List[str]]:
    """
    Route to sheets within a dataset using SHEET_REGISTRY.
    
    Returns:
        List of canonical sheet names, or None if no sheet restriction
    
    Examples:
        "data domestic" + Overview Vessel → ["DOMESTIC"]
        "data international" + Container Throughput → ["Internasional"]
        No sheet keyword → None (all sheets)
    """
    question = sanitize_leading_number(question)
    question_lower = question.lower()
    
    if dataset not in SHEET_REGISTRY:
        return None
    
    sheet_map = SHEET_REGISTRY[dataset]
    matched_sheets = []
    
    for alias, canonical_name in sheet_map.items():
        if alias.lower() in question_lower:
            if canonical_name not in matched_sheets:
                matched_sheets.append(canonical_name)
    
    # If no sheet keywords found, return None (query all sheets)
    return matched_sheets if matched_sheets else None


def resolve_entities(
    question: str,
    dataset: Optional[str] = None,
) -> ResolvedEntities:
    """
    Resolve entities from question: operators, metrics, columns, month, year.
    
    Does NOT interpret:
    - Aggregation functions (tertinggi → MAX)
    - Query intent (comparison, ranking, etc.)
    
    Args:
        question: User's natural language question
        dataset: Dataset context for schema-aware resolution
    
    Returns:
        ResolvedEntities with operators, metrics, columns, month
    """
    question = sanitize_leading_number(question)
    question_lower = question.lower()
    
    # Resolve operators with word boundaries
    operators = []
    for op in OPERATORS:
        if op.upper() == "YANG":
            has_yang = (
                re.search(r'\b(YANG|Yang)\b', question) is not None or
                re.search(r'\byang\s+ming\b', question_lower) is not None or
                re.search(r'\b(operator|pelayaran)\s+yang\b', question_lower) is not None
            )
            if not has_yang:
                continue

        pattern = r'\b' + re.escape(op.lower()) + r'\b'
        if re.search(pattern, question_lower):
            operators.append(op)
    
    # Resolve metrics and columns
    metrics = []
    columns = []
    
    # Check aliases first
    for alias, canonical_col in COLUMN_ALIASES.items():
        # Match alias as whole word or part of word (e.g., "productivity" matches "produktivitas")
        if alias.lower() in question_lower:
            if canonical_col not in metrics:
                metrics.append(canonical_col)
            if canonical_col not in columns:
                columns.append(canonical_col)
    
    # Also check for Indonesian variants
    indonesian_aliases = {
        "produktivitas": "BCH",
        "produktifitas": "BCH",
        "pendapatan": "TOTAL ALL REVENUE",
        "revenue": "TOTAL ALL REVENUE",
        "penerimaan": "TOTAL ALL REVENUE",
    }
    for alias, canonical_col in indonesian_aliases.items():
        if alias.lower() in question_lower:
            if canonical_col not in metrics:
                metrics.append(canonical_col)
            if canonical_col not in columns:
                columns.append(canonical_col)
    
    # Check direct column mentions from schema
    if dataset:
        schema = get_schema(dataset, db_schema=None)
        schema_columns = schema.get("columns", [])
        for col in schema_columns:
            # Check for direct column mention (case-insensitive, word boundary)
            pattern = r'\b' + re.escape(col.lower()) + r'\b'
            if re.search(pattern, question_lower):
                if col not in metrics:
                    metrics.append(col)
                if col not in columns:
                    columns.append(col)
                    
        # Context-aware refinement
        if dataset == "Overview Vessel":
            if "aktivitas" in question_lower and "TEUS" not in metrics:
                metrics.append("TEUS")
        elif dataset == "Container Throughput":
            if "actual" in question_lower or "throughput" in question_lower:
                if "ACTUAL" not in metrics and "ACTUAL" in schema_columns:
                    metrics.append("ACTUAL")
            if "TEUS" in metrics and "TEUS" not in schema_columns and "ACTUAL" in schema_columns:
                metrics = [m for m in metrics if m != "TEUS"]
                if "ACTUAL" not in metrics:
                    metrics.append("ACTUAL")
        elif dataset == "Realisasi UC":
            if "TEUS" in metrics and "TEUS" not in schema_columns and "TOTAL TEUS" in schema_columns:
                metrics = ["TOTAL TEUS" if m == "TEUS" else m for m in metrics]
        elif dataset == "Komersial Dashboard":
            if ("pendapatan" in question_lower or "revenue" in question_lower) and "TOTAL ALL REVENUE" in schema_columns:
                if "TOTAL ALL REVENUE" not in metrics:
                    metrics.append("TOTAL ALL REVENUE")
            if "TOTAL REVENUE" in metrics and "TOTAL ALL REVENUE" in schema_columns:
                metrics = ["TOTAL ALL REVENUE" if m == "TOTAL REVENUE" else m for m in metrics]
        elif dataset == "RestNDisc":
            # For RestNDisc, avoid defaulting to TEUS
            metrics = [m for m in metrics if m != "TEUS"]
            if ("nominal" in question_lower or "keringanan" in question_lower or "persetujuan" in question_lower) and "NOMINAL PERSETUJUAN KERINGANAN" in schema_columns:
                if "NOMINAL PERSETUJUAN KERINGANAN" not in metrics:
                    metrics.append("NOMINAL PERSETUJUAN KERINGANAN")
    
    # Resolve month and year
    month_context = _resolve_month_and_year(question)
    
    return ResolvedEntities(
        operators=operators,
        metrics=metrics,
        columns=columns,
        month=month_context
    )


def resolve_columns(
    metrics: List[str],
    dataset: str,
    schema: Optional[dict] = None,
) -> List[str]:
    """
    Resolve metric names to canonical column names using aliases and schema validation.
    
    Args:
        metrics: List of metric names (may include aliases)
        dataset: Dataset name for schema validation
        schema: Optional DB schema (if None, uses static registry)
    
    Returns:
        List of validated canonical column names
    """
    columns = []
    
    for metric in metrics:
        # Check if it's an alias
        canonical = COLUMN_ALIASES.get(metric.lower())
        if canonical:
            metric = canonical
        
        # Validate against schema
        if validate_column(metric, dataset, db_schema=schema):
            if metric not in columns:
                columns.append(metric)
    
    return columns


def normalize_month(month_text: Optional[str]) -> Optional[MonthContext]:
    """
    Normalize month reference to MonthContext.
    
    Supports:
    - English: January, February, ..., December
    - Indonesian: Januari, Februari, ..., Desember
    - Abbreviated: Jan, Feb, Mar, ..., Dec
    - Numeric: 1, 2, 3, ..., 12
    
    Args:
        month_text: Month string in various formats
    
    Returns:
        MonthContext with normalized Indonesian name and code, or None if invalid
    """
    if not month_text:
        return None
    
    month_key = month_text.lower().strip()
    
    if month_key in MONTH_NORMALIZE_MAP:
        normalized = MONTH_NORMALIZE_MAP[month_key]
        return MonthContext(
            month_str=normalized["id"],
            month_code=normalized["code"],
            year=0  # Year must be provided separately
        )
    
    return None


def _resolve_month_and_year(question: str) -> Optional[MonthContext]:
    """
    Internal helper to resolve both month and year from question.
    
    Returns:
        MonthContext with month, code, and year, or None if not found
    """
    question_lower = question.lower()
    
    # Extract year (4-digit number)
    year_match = re.search(r'\b(20\d{2})\b', question)
    year = int(year_match.group(1)) if year_match else 0
    
    # Extract month
    month_context = None
    
    # Try to find month names/codes in question
    for month_key, month_data in MONTH_NORMALIZE_MAP.items():
        # Check for month mention (word boundary to avoid partial matches)
        pattern = r'\b' + re.escape(month_key) + r'\b'
        if re.search(pattern, question_lower):
            month_context = MonthContext(
                month_str=month_data["id"],
                month_code=month_data["code"],
                year=year
            )
            break  # Take first match
    
    # If we found a year but no month, still return context with year
    if year > 0 and not month_context:
        month_context = MonthContext(
            month_str="",
            month_code=0,
            year=year
        )
    
    return month_context
