"""
Dynamic Schema & Distinct Value Sampler Module.
Universally inspects dataset DataFrames and extracts categorical distinct value samples.
Enables 100% hardcode-free Text-to-SQL query classification and filter construction.
"""

import logging
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)

# Cache for distinct value samples per source_id
_SCHEMA_SAMPLE_CACHE: Dict[str, Dict[str, List[str]]] = {}


def get_dataset_schema_and_samples(df: pd.DataFrame, source_id: Optional[str] = None) -> Dict[str, List[str]]:
    """
    Extracts column names and unique non-empty string values for categorical/text columns.
    
    Args:
        df: Input pandas DataFrame for a dataset
        source_id: Optional source identifier for caching
        
    Returns:
        Dict mapping column_name -> list of unique sample values
    """
    if source_id and source_id in _SCHEMA_SAMPLE_CACHE:
        return _SCHEMA_SAMPLE_CACHE[source_id]

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
            unique_vals = [
                str(val).strip() for val in series.unique() 
                if val is not None and str(val).strip() and str(val).strip().lower() != 'nan'
            ]
            # Keep up to 50 distinct sample values for matching
            if unique_vals:
                samples[col_clean] = unique_vals[:50]
                
    if source_id:
        _SCHEMA_SAMPLE_CACHE[source_id] = samples
        
    return samples


def clear_schema_sample_cache(source_id: Optional[str] = None):
    """Clear schema sample cache."""
    if source_id:
        _SCHEMA_SAMPLE_CACHE.pop(source_id, None)
    else:
        _SCHEMA_SAMPLE_CACHE.clear()
