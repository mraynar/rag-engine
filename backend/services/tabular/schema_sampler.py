"""
Dynamic Schema & Distinct Value Sampler Module.
Universally inspects dataset DataFrames and extracts categorical distinct value samples.
Enables 100% hardcode-free Text-to-SQL query classification and filter construction.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

import time

# Cache for distinct value samples per source_id with TTL timestamp (60 minutes)
_SCHEMA_SAMPLE_CACHE: Dict[str, tuple[float, Dict[str, List[str]]]] = {}
_CACHE_TTL_SECONDS = 3600.0


def clear_schema_sample_cache(source_id: Optional[str] = None) -> None:
    """Clear schema sample cache for a specific source_id or all sources."""
    global _SCHEMA_SAMPLE_CACHE
    if source_id:
        _SCHEMA_SAMPLE_CACHE.pop(source_id, None)
    else:
        _SCHEMA_SAMPLE_CACHE.clear()


def get_dataset_schema_and_samples(df: pd.DataFrame, source_id: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Extracts column names and unique non-empty string values for categorical/text columns.
    Uses ultra-fast Shared Schema Memory Cache (< 5ms response time).
    """
    now = time.time()
    if source_id and source_id in _SCHEMA_SAMPLE_CACHE:
        ts, cached_samples = _SCHEMA_SAMPLE_CACHE[source_id]
        if now - ts < _CACHE_TTL_SECONDS:
            return cached_samples

    if df.empty:
        return {}

    samples: Dict[str, List[str]] = {}
    
    excluded_cols = {"id", "created_at", "updated_at", "source_id", "row_index", "_sheet", "date", "tanggal", "timestamp"}
    
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean.lower() in excluded_cols:
            continue
            
        series = df[col].dropna()
        if series.empty:
            continue
            
        # Check if column is string/categorical or contains text values
        if series.dtype == 'object' or isinstance(series.iloc[0], str):
            unique_vals = []
            for val in series.unique():
                val_str = str(val).strip()
                if val_str and val_str.lower() not in ('nan', 'none', 'null') and val_str not in unique_vals:
                    unique_vals.append(val_str)
                    if len(unique_vals) >= 5:
                        break
            if unique_vals:
                samples[col_clean] = unique_vals
                
    if source_id:
        _SCHEMA_SAMPLE_CACHE[source_id] = (now, samples)
        
    return samples


def format_schema_samples_for_llm(samples: Dict[str, List[str]]) -> str:
    """Format column schema and value samples into a clean text block for LLM prompts."""
    if not samples:
        return "Tutup sampel nilai kolom."
    lines = []
    for col, vals in samples.items():
        vals_str = ", ".join([f"'{v}'" for v in vals[:5]])
        lines.append(f"- Kolom `{col}` (Sampel Nilai Unik: {vals_str})")
    return "\n".join(lines)


def clear_schema_sample_cache(source_id: Optional[str] = None):
    """Clear schema sample cache."""
    if source_id:
        _SCHEMA_SAMPLE_CACHE.pop(source_id, None)
    else:
        _SCHEMA_SAMPLE_CACHE.clear()

