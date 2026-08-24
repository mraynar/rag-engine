"""
Retry Engine module using the Strategy Pattern to recover from failed queries.
Part of the Phase 2G implementation (TDD Green Phase).
"""
from dataclasses import replace
from typing import Optional, List, Dict, Any

from app.services.tabular.domain_models import (
    QueryPlan,
    FilterCondition,
    FilterOperator,
    AggregationSpec,
    ExecutionResult,
    ResultQuality,
    ResolvedEntities,
    RetryStrategy,
)
from app.services.tabular.executor import execute_query


class RetryStrategyBase:
    """Base class for all retry strategies."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        raise NotImplementedError("Subclasses must implement apply()")


class MonthRetry(RetryStrategyBase):
    """Retries query by converting English or numeric month filters to Indonesian."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        new_filters = []
        modified = False
        from app.services.tabular.registries import MONTH_NORMALIZE_MAP

        for f in plan.filters:
            if f.column.upper() in ["MONTH", "MONTH_CODE", "BULAN"]:
                val_str = str(f.value).lower().strip()
                if val_str in MONTH_NORMALIZE_MAP:
                    norm = MONTH_NORMALIZE_MAP[val_str]
                    # Map to code if MONTH_CODE, else id (Indonesian string)
                    new_val = norm["code"] if f.column.upper() == "MONTH_CODE" else norm["id"]
                    if f.value != new_val:
                        new_filters.append(replace(f, value=new_val))
                        modified = True
                        continue
            new_filters.append(f)

        if modified:
            return replace(plan, filters=new_filters)
        return None


class SheetRetry(RetryStrategyBase):
    """Retries query by trying the alternative sheet name in schema."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        sheets = schema.get("sheets", [])
        if len(sheets) <= 1:
            return None

        if plan.sheet:
            current_sheet = plan.sheet.upper()
            alt_sheet = next((s for s in sheets if s.upper() != current_sheet), None)
            if alt_sheet:
                return replace(plan, sheet=alt_sheet)
        else:
            return replace(plan, sheet=sheets[0])
        return None


class ColumnRetry(RetryStrategyBase):
    """Retries query by resolving metric mapping to fallback column alias."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        if plan.aggregation and plan.aggregation.column:
            col = plan.aggregation.column.lower().strip()
            from app.services.tabular.registries import COLUMN_ALIASES
            if col in COLUMN_ALIASES:
                alt_col = COLUMN_ALIASES[col]
                columns = schema.get("columns", [])
                if any(c.lower() == alt_col.lower() for c in columns):
                    correct_cased_col = next((c for c in columns if c.lower() == alt_col.lower()), alt_col)
                    new_agg = replace(plan.aggregation, column=correct_cased_col)
                    return replace(plan, aggregation=new_agg)
        return None


class OperatorRetry(RetryStrategyBase):
    """Retries query by normalizing operator filter values."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        new_filters = []
        modified = False
        from app.services.tabular.registries import OPERATORS

        for f in plan.filters:
            if f.column.upper() in ["LOP", "OPERATOR", "VESSEL OPERATOR"]:
                val_str = str(f.value).upper().strip()
                if val_str not in OPERATORS:
                    matched = next((op for op in OPERATORS if op.lower() == val_str.lower()), None)
                    if matched and f.value != matched:
                        new_filters.append(replace(f, value=matched))
                        modified = True
                        continue
            new_filters.append(f)

        if modified:
            return replace(plan, filters=new_filters)
        return None


class RelaxedFilterRetry(RetryStrategyBase):
    """Retries query by progressively relaxing the non-essential filters."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        if not plan.filters:
            return None

        # Filter out YEAR column to preserve core temporal context
        year_filters = [f for f in plan.filters if f.column.upper() == "YEAR"]
        other_filters = [f for f in plan.filters if f.column.upper() != "YEAR"]

        if other_filters:
            # Relax one non-essential filter from the end
            new_filters = year_filters + other_filters[:-1]
            return replace(plan, filters=new_filters)
        elif len(year_filters) > 1:
            return replace(plan, filters=year_filters[:-1])

        return None


class AggregationRetry(RetryStrategyBase):
    """Retries query by applying fallback aggregation functions."""
    def apply(self, plan: QueryPlan, resolved: ResolvedEntities, schema: dict) -> Optional[QueryPlan]:
        if plan.aggregation:
            if plan.aggregation.func in ["max", "min", "mean"]:
                new_agg = replace(plan.aggregation, func="sum")
                return replace(plan, aggregation=new_agg)
            elif plan.aggregation.func == "sum":
                new_agg = replace(plan.aggregation, func="count", column=None)
                return replace(plan, aggregation=new_agg)
        return None


def plan_signature(plan: QueryPlan) -> tuple:
    """Helper to create a unique hashable representation of a QueryPlan."""
    filters_tuple = tuple((f.column, f.operator.value, str(f.value)) for f in plan.filters)
    agg_tuple = (plan.aggregation.func, plan.aggregation.column) if plan.aggregation else None
    group_by_tuple = tuple(plan.group_by) if plan.group_by else None
    return (plan.sheet, filters_tuple, agg_tuple, group_by_tuple, plan.sort, plan.limit)


def get_strategy_enum(strategy: RetryStrategyBase) -> RetryStrategy:
    """Helper to map a strategy class name to its domain model enum."""
    name = strategy.__class__.__name__
    return {
        "MonthRetry": RetryStrategy.MONTH_RETRY,
        "SheetRetry": RetryStrategy.SHEET_RETRY,
        "ColumnRetry": RetryStrategy.COLUMN_RETRY,
        "OperatorRetry": RetryStrategy.OPERATOR_RETRY,
        "RelaxedFilterRetry": RetryStrategy.RELAXED_FILTER_RETRY,
        "AggregationRetry": RetryStrategy.AGGREGATION_RETRY,
    }.get(name)


def execute_with_retry(
    source_id: str,
    plan: QueryPlan,
    question: str,
    resolved: ResolvedEntities,
    dataset: str,
    max_retries: int = 3,
    db_schema: Optional[dict] = None
) -> ExecutionResult:
    """
    Main orchestrator for QueryPlan execution with strategy retries.
    
    Args:
        source_id: UUID of the data source
        plan: Base QueryPlan
        question: Question string
        resolved: Extracted ResolvedEntities context
        dataset: Target dataset name
        max_retries: Max number of retried executions
        db_schema: Optional DB schema
        
    Returns:
        ExecutionResult (either VALID or latest fallback result)
    """
    from app.services.tabular.schema_registry import get_schema
    schema = get_schema(dataset, db_schema)

    df_cache = {}
    result = execute_query(source_id, plan, db_schema, df_cache=df_cache)
    if result.quality in [ResultQuality.VALID, ResultQuality.ALL_ZERO]:
        return result

    strategies = [
        MonthRetry(),
        SheetRetry(),
        ColumnRetry(),
        OperatorRetry(),
        RelaxedFilterRetry(),
        AggregationRetry(),
    ]

    retry_count = 0
    last_strategy = None
    tried_plans = {plan_signature(plan)}

    for strategy in strategies:
        if retry_count >= max_retries:
            break

        new_plan = strategy.apply(plan, resolved, schema)
        if new_plan is None:
            continue

        sig = plan_signature(new_plan)
        if sig in tried_plans:
            continue

        tried_plans.add(sig)
        retry_count += 1

        new_result = execute_query(source_id, new_plan, db_schema, df_cache=df_cache)
        strategy_enum_val = get_strategy_enum(strategy)
        
        new_result.retry_count = retry_count
        new_result.last_retry_strategy = strategy_enum_val

        if new_result.quality in [ResultQuality.VALID, ResultQuality.ALL_ZERO]:
            return new_result

        result = new_result
        last_strategy = strategy_enum_val

    result.retry_count = retry_count
    result.last_retry_strategy = last_strategy
    return result
