"""
Dekomposisi query kompleks (multi-hop / perbandingan) menjadi SubQuery.
"""
import re
from typing import List, Optional
from backend.services.tabular.domain_models import (
    QueryAST,
    QueryType,
    UserIntent,
    SubQuery,
    ResolvedEntities,
)


def decompose_query(
    ast: QueryAST,
    question: str,
    resolved: ResolvedEntities,
    dataset: Optional[str] = None
) -> List[SubQuery]:
    """
    Decompose QueryAST into list of SubQuery execution steps.
    
    Args:
        ast: Classified QueryAST
        question: Original user question
        resolved: Resolved entities from resolver
        dataset: Dataset name for context
    
    Returns:
        List of SubQuery objects (1 for simple, 2+ for multi-hop)
    """
    # Most queries do not require decomposition
    if ast.query_type in [QueryType.SIMPLE, QueryType.AGGREGATION, 
                           QueryType.RANKING, QueryType.TREND]:
        return _create_single_subquery(ast, question)
    
    # Multi-hop queries require analysis
    if ast.query_type == QueryType.MULTI_HOP or ast.intent == UserIntent.MULTI_HOP:
        return _decompose_multihop(ast, question, resolved, dataset)
    
    # Comparison queries may or may not require decomposition
    if ast.query_type == QueryType.COMPARISON or ast.intent == UserIntent.COMPARISON:
        return _decompose_comparison(ast, question, resolved, dataset)
    
    # Fallback: single SubQuery
    return _create_single_subquery(ast, question)


def _create_single_subquery(ast: QueryAST, question: str) -> List[SubQuery]:
    """
    Create single SubQuery for non-decomposable queries.
    
    Args:
        ast: QueryAST
        question: Original question
    
    Returns:
        List containing single SubQuery
    """
    return [SubQuery(
        step=1,
        question=question,
        template_type=ast.query_type,
        depends_on=None
    )]


def _decompose_multihop(
    ast: QueryAST,
    question: str,
    resolved: ResolvedEntities,
    dataset: Optional[str]
) -> List[SubQuery]:
    """
    Decompose multi-hop queries into SubQuery steps.
    
    Detects patterns:
    - Year comparisons: "2024 dan 2025", "selisih 2024 dan 2025"
    - Category comparisons: "domestic dan international"
    - Operator comparisons: "TIL dan SPI"
    
    Args:
        ast: QueryAST
        question: Original question
        resolved: ResolvedEntities
        dataset: Dataset name
    
    Returns:
        List of SubQuery objects (2+ for true multi-hop)
    """
    question_lower = question.lower()

    annual_monthly_terms = ["berbeda", "bandingkan", "dibanding", "selisih"]
    year_match = re.search(r'\b(20\d{2})\b', question_lower)
    if "per bulan" in question_lower and year_match and any(term in question_lower for term in annual_monthly_terms):
        year = year_match.group(1)
        metric = resolved.metrics[0] if resolved.metrics else "TEUS"
        return [
            SubQuery(
                step=1,
                question=f"Berapa total {metric} tahun {year}?",
                template_type=QueryType.AGGREGATION,
                depends_on=None,
            ),
            SubQuery(
                step=2,
                question=f"Berapa total {metric} per bulan tahun {year}?",
                template_type=QueryType.TREND,
                depends_on=None,
            ),
        ]
    
    # Pattern 1: Year comparison ("2024 dan 2025", "selisih 2024 dan 2025")
    year_pattern = r'\b(20\d{2})\b.*(?:dan|vs|versus).*\b(20\d{2})\b'
    year_match = re.search(year_pattern, question_lower)
    
    if year_match:
        year1 = int(year_match.group(1))
        year2 = int(year_match.group(2))
        return _create_year_comparison_subqueries(question, year1, year2, ast, resolved)
    
    # Pattern 2: Category comparison ("domestic dan international")
    category_pattern = r'\b(domestic|domestik|international|internasional)\b.*(?:dan|vs|versus).*\b(domestic|domestik|international|internasional)\b'
    category_match = re.search(category_pattern, question_lower)
    
    if category_match:
        # This COULD be a single-query comparison with GROUP BY
        # For now, treat as single SubQuery (query builder decides grouping)
        return _create_single_subquery(ast, question)
    
    # Pattern 3: Operator comparison ("TIL dan SPI")
    if len(resolved.operators) >= 2 and ('dan' in question_lower or 'vs' in question_lower):
        # Multiple operators can be handled with IN filter (single query)
        return _create_single_subquery(ast, question)
    
    # Pattern 4: Month comparison ("Januari dan Februari")
    month_pattern = r'\b(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\b.*(?:dan|vs|versus).*\b(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)\b'
    month_match = re.search(month_pattern, question_lower)
    
    if month_match:
        month1 = month_match.group(1).capitalize()
        month2 = month_match.group(2).capitalize()
        return _create_month_comparison_subqueries(question, month1, month2, ast, resolved)
    
    # Pattern 5: Percentage contribution of a sheet ("persentase kontribusi internasional")
    if "persentase" in question_lower or "kontribusi" in question_lower or "%" in question_lower:
        target_sheet = None
        if any(w in question_lower for w in ["internasional", "international"]):
            target_sheet = "INTERNATIONAL"
        elif any(w in question_lower for w in ["domestik", "domestic"]):
            target_sheet = "DOMESTIC"
            
        year_match = re.search(r'\b(20\d{2})\b', question_lower)
        year_str = f" tahun {year_match.group(1)}" if year_match else ""
        
        if target_sheet:
            metric = resolved.metrics[0] if resolved.metrics else "TEUS"
            subquery1 = SubQuery(
                step=1,
                question=f"Berapa total {metric} {target_sheet.lower()}{year_str}?",
                template_type=QueryType.AGGREGATION,
                depends_on=None
            )
            subquery2 = SubQuery(
                step=2,
                question=f"Berapa total {metric}{year_str}?",
                template_type=QueryType.AGGREGATION,
                depends_on=None
            )
            return [subquery1, subquery2]

    # No clear decomposition pattern found - return single SubQuery
    # Query builder may fall back to LLM if needed
    return _create_single_subquery(ast, question)


def _decompose_comparison(
    ast: QueryAST,
    question: str,
    resolved: ResolvedEntities,
    dataset: Optional[str]
) -> List[SubQuery]:
    """
    Decompose comparison queries.
    
    Some comparisons are single-query (GROUP BY), others are multi-hop.
    
    Args:
        ast: QueryAST
        question: Original question
        resolved: ResolvedEntities
        dataset: Dataset name
    
    Returns:
        List of SubQuery objects
    """
    # Delegate to multi-hop decomposer for now
    return _decompose_multihop(ast, question, resolved, dataset)


def _create_year_comparison_subqueries(
    question: str,
    year1: int,
    year2: int,
    ast: QueryAST,
    resolved: ResolvedEntities
) -> List[SubQuery]:
    """
    Create SubQueries for year-based comparison.
    
    Args:
        question: Original question
        year1: First year
        year2: Second year
        ast: QueryAST
        resolved: ResolvedEntities
    
    Returns:
        Two SubQueries (one for each year)
    """
    # Extract metric from question
    metric = resolved.metrics[0] if resolved.metrics else "nilai"
    
    # Create SubQuery 1: First year
    subquery1 = SubQuery(
        step=1,
        question=f"Berapa total {metric} tahun {year1}?",
        template_type=QueryType.AGGREGATION,
        depends_on=None
    )
    
    # Create SubQuery 2: Second year
    subquery2 = SubQuery(
        step=2,
        question=f"Berapa total {metric} tahun {year2}?",
        template_type=QueryType.AGGREGATION,
        depends_on=None  # Parallel execution (no dependency)
    )
    
    return [subquery1, subquery2]


def _create_month_comparison_subqueries(
    question: str,
    month1: str,
    month2: str,
    ast: QueryAST,
    resolved: ResolvedEntities
) -> List[SubQuery]:
    """
    Create SubQueries for month-based comparison.
    
    Args:
        question: Original question
        month1: First month
        month2: Second month
        ast: QueryAST
        resolved: ResolvedEntities
    
    Returns:
        Two SubQueries (one for each month)
    """
    metric = resolved.metrics[0] if resolved.metrics else "nilai"
    
    # Extract year if present
    year_match = re.search(r'\b(20\d{2})\b', question)
    year_str = f" tahun {year_match.group(1)}" if year_match else ""
    
    subquery1 = SubQuery(
        step=1,
        question=f"Berapa total {metric} {month1}{year_str}?",
        template_type=QueryType.AGGREGATION,
        depends_on=None
    )
    
    subquery2 = SubQuery(
        step=2,
        question=f"Berapa total {metric} {month2}{year_str}?",
        template_type=QueryType.AGGREGATION,
        depends_on=None
    )
    
    return [subquery1, subquery2]
