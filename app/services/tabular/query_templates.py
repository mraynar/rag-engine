"""
Query Templates: Reusable execution intent definitions.

Responsibilities:
- Define semantic templates for each QueryType and UserIntent
- Specify aggregation, grouping, sorting requirements
- Abstract operator/temporal dimensions (not physical column names)

Does NOT:
- Query database
- Call Gemini API
- Execute pandas operations
- Resolve physical column names
- Perform arithmetic
- Modify QueryAST or QueryPlan after construction
"""
from typing import Dict, Any, Optional
from app.services.tabular.domain_models import QueryType, UserIntent


# Template registry mapping (QueryType, UserIntent) → template dict
TEMPLATE_REGISTRY: Dict[QueryType, Dict[UserIntent, Dict[str, Any]]] = {
    QueryType.SIMPLE: {
        UserIntent.VALUE_LOOKUP: {
            "requires_aggregation": False,
            "requires_grouping": False,
            "requires_sorting": False,
            "default_limit": None,
            "description": "Simple value lookup without aggregation"
        },
        UserIntent.PERCENTAGE_LOOKUP: {
            "requires_aggregation": False,
            "requires_grouping": False,
            "requires_sorting": False,
            "default_limit": None,
            "description": "Percentage value lookup (data already contains %)"
        }
    },
    
    QueryType.AGGREGATION: {
        UserIntent.TOTAL_AGGREGATION: {
            "requires_aggregation": True,
            "requires_grouping": False,
            "requires_sorting": False,
            "default_agg_func": "sum",
            "default_limit": None,
            "description": "Total/sum aggregation across all matching rows"
        }
    },
    
    QueryType.RANKING: {
        UserIntent.TOP_N: {
            "requires_aggregation": True,
            "requires_grouping": True,
            "requires_sorting": True,
            "default_agg_func": "max",
            "grouping_dimension": "operator",  # Abstract: resolved by query builder
            "sort_order": "desc",
            "default_limit": 1,
            "description": "Ranking query for highest/maximum values"
        },
        UserIntent.BOTTOM_N: {
            "requires_aggregation": True,
            "requires_grouping": True,
            "requires_sorting": True,
            "default_agg_func": "min",
            "grouping_dimension": "operator",  # Abstract: resolved by query builder
            "sort_order": "asc",
            "default_limit": 1,
            "description": "Ranking query for lowest/minimum values"
        }
    },
    
    QueryType.TREND: {
        UserIntent.TREND_ANALYSIS: {
            "requires_aggregation": True,
            "requires_grouping": True,
            "requires_sorting": False,
            "default_agg_func": "sum",
            "grouping_dimension": "temporal",
            "default_limit": None,
            "description": "Trend analysis over time periods"
        }
    },
    
    QueryType.MULTI_HOP: {
        UserIntent.MULTI_HOP: {
            "requires_decomposition": True,
            "requires_aggregation": False,  # Determined per SubQuery
            "requires_grouping": False,  # Determined per SubQuery
            "requires_sorting": False,
            "default_limit": None,
            "description": "Multi-hop query requiring decomposition into SubQueries"
        },
        UserIntent.COMPARISON: {
            "requires_decomposition": True,
            "requires_aggregation": False,
            "requires_grouping": False,
            "requires_sorting": False,
            "default_limit": None,
            "description": "Comparison query potentially requiring decomposition"
        }
    },
    
    QueryType.COMPARISON: {
        UserIntent.COMPARISON: {
            "requires_decomposition": True,
            "requires_aggregation": False,
            "requires_grouping": False,
            "requires_sorting": False,
            "default_limit": None,
            "description": "Comparison query (may or may not require multi-hop)"
        }
    }
}


def get_template(
    query_type: QueryType,
    intent: UserIntent
) -> Dict[str, Any]:
    """
    Get execution template for given QueryType and UserIntent.
    
    Args:
        query_type: Type of query operation
        intent: Fine-grained user intent
    
    Returns:
        Template dictionary with execution requirements
    """
    # Try exact match first
    if query_type in TEMPLATE_REGISTRY:
        if intent in TEMPLATE_REGISTRY[query_type]:
            return TEMPLATE_REGISTRY[query_type][intent].copy()
        
        # Fallback to first template for this query type
        if TEMPLATE_REGISTRY[query_type]:
            first_template = next(iter(TEMPLATE_REGISTRY[query_type].values()))
            return first_template.copy()
    
    # Ultimate fallback: simple template
    return {
        "requires_aggregation": False,
        "requires_grouping": False,
        "requires_sorting": False,
        "default_limit": None,
        "description": "Fallback template for unknown query type/intent"
    }


def get_grouping_dimension_column(
    grouping_dimension: str,
    dataset: Optional[str] = None,
    question: Optional[str] = None
) -> Optional[str]:
    """
    Resolve abstract grouping dimension to physical column hint.
    
    NOTE: This is a HINT only. The query builder must validate against schema.
    
    Args:
        grouping_dimension: Abstract dimension ("operator", "temporal", etc.)
        dataset: Dataset name for context
        question: Question text for context
    
    Returns:
        Column name hint or None if cannot determine
    """
    if grouping_dimension == "operator":
        # Return abstract hint - query builder resolves to LOP or OPERATOR
        return "operator_dimension"
    
    elif grouping_dimension == "temporal":
        # Detect whether monthly or yearly grouping from question
        if question:
            question_lower = question.lower()
            if "tahun berapa" in question_lower:
                return "YEAR"
            if any(kw in question_lower for kw in ["per bulan", "bulanan", "monthly", "bulan"]):
                return "MONTH"
            elif any(kw in question_lower for kw in ["per tahun", "tahunan", "yearly", "annual", "tahun"]):
                return "YEAR"
        
        # Default: monthly for trend analysis
        return "MONTH"
    
    return None
