"""
Schema registry and validation functions for datasets.
"""
from typing import Optional, Dict, List

# Static schema fallback for known datasets
SCHEMA_REGISTRY = {
    "Overview Vessel": {
        "sheets": ["DOMESTIC", "INTERNATIONAL"],
        "columns": ["YEAR", "MONTH", "LOP", "TEUS", "Boxes", "BCH", "BSH"]
    },
    "Container Throughput": {
        "sheets": ["Domestik", "Internasional"],
        "columns": ["YEAR", "MONTH", "ACTUAL", "BUDGET", "ACTUAL VS BUDGET"]
    },
    "Market Share": {
        "sheets": ["V.OPR DOM", "V.OPR INT"],
        "columns": ["YEAR", "MONTH", "OPERATOR", "%"]
    },
    "Transhipment": {
        "sheets": ["Transhipment"],
        "columns": ["YEAR", "MONTH", "20'", "40'", "VESSEL OPERATOR"]
    }
}


def get_schema(dataset_name: str, db_schema: Optional[Dict] = None) -> Dict:
    """
    Get schema for a dataset, merging DB schema with static fallback.
    
    Args:
        dataset_name: Name of the dataset
        db_schema: Optional schema from database (dict of sheet_name -> [columns])
    
    Returns:
        Dict with 'sheets' and 'columns' keys, or empty dict if dataset unknown
    """
    # If db_schema is provided and not empty, use it
    if db_schema:
        sheets = list(db_schema.keys())
        # Flatten and deduplicate columns from all sheets
        columns = []
        seen = set()
        for sheet_columns in db_schema.values():
            for col in sheet_columns:
                if col not in seen:
                    columns.append(col)
                    seen.add(col)
        return {"sheets": sheets, "columns": columns}
    
    # Fallback to static registry
    if dataset_name in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[dataset_name]
    
    # Unknown dataset
    return {}


def validate_column(column: Optional[str], dataset: str, db_schema: Optional[Dict] = None) -> bool:
    """
    Check if a column exists in the dataset schema (case-insensitive).
    
    Args:
        column: Column name to validate
        dataset: Dataset name
        db_schema: Optional DB schema
    
    Returns:
        True if column exists, False otherwise
    """
    if column is None:
        return True
        
    schema = get_schema(dataset, db_schema)
    if not schema:
        return False
    
    columns = schema.get("columns", [])
    column_lower = column.lower()
    return any(col.lower() == column_lower for col in columns)


def validate_sheet(sheet: str, dataset: str, db_schema: Optional[Dict] = None) -> bool:
    """
    Check if a sheet exists in the dataset schema (case-insensitive).
    
    Args:
        sheet: Sheet name to validate
        dataset: Dataset name
        db_schema: Optional DB schema
    
    Returns:
        True if sheet exists, False otherwise
    """
    schema = get_schema(dataset, db_schema)
    if not schema:
        return False
    
    sheets = schema.get("sheets", [])
    return any(s.strip().lower() == sheet.strip().lower() for s in sheets)
