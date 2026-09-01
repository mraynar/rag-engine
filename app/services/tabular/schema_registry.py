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
    "Realisasi UC": {
        "sheets": ["SUMMARY", "OH OW OL", "TREND UC", "_all_sheets"],
        "columns": [
            "TAHUN", "BULAN", "STATUS", "20'", "40'", "45'",
            "TOTAL BOX", "TOTAL TEUS", "TOTAL", "TOTAL DISCOUNT",
            "TOTAL REVENUE", "KEGIATAN", "ACTIVITY", "DATE", "MONTH",
            "YEAR", "URUTAN", "KATEGORI", "UNNAMED: 12"
        ]
    },
    "Market Share": {
        "sheets": ["V.OPR DOM", "V.OPR INT"],
        "columns": ["YEAR", "MONTH", "LOP", "%"]
    },
    "Transhipment": {
        # Actual sheets in DB: 'new vr', 'Transhipment ', 'VR', 'YR...' etc.
        # Main revenue sheet: 'new vr'
        "sheets": ["new vr", "Transhipment", "VR"],
        "columns": [
            "YEAR", "BULAN", "MONTH", "20'", "40'", "VESSEL OPERATOR",
            "VESSEL REVENUE", "VESSEL REVENUE 2024", "VESSEL REVENUE 2025",
            "KATEGORI", "BOXES 2024", "BOXES 2025"
        ]
    },
    "RestNDisc": {
        "sheets": ["Form Responses 1"],
        "columns": [
            "STATUS", "AKTIVITAS", "TIMESTAMP", "NAMA PERUSAHAAN",
            "SUPPORTING DOCUMENT", "NOMOR JASA KEPELABUHAN", "NOMOR SURAT JAWABAN TPS",
            "TANGGAL SURAT JAWABAN TPS", "NOMOR MASTER PELANGGAN TPS",
            "NOMINAL PERSETUJUAN KERINGANAN"
        ]
    },
    "Komersial Dashboard": {
        "sheets": ["DATA KOMERSIAL"],
        "columns": [
            "YEAR", "MONTH", "BULAN", "VESSEL OPERATOR", "TOTAL REVENUE",
            "TOTAL ALL REVENUE", "TOTAL TEUS", "TEUS FULL", "TEUS EMPTY",
            "TOTAL BOX", "BOX", "DN / LN", "EXPORT/IMPORT"
        ]
    },
    "Vessel Service": {
        "sheets": ["New"],
        "columns": [
            "YEAR", "MONTH", "VESSEL OPERATOR", "SERVICE", "ROUTES",
            "TOTAL CALL", "TEUS", "BOXES", "MOVES", "BMPH", "GMPH",
            "AVERAGE BMPH", "AVERAGE GMPH", "AVERAGE TEUS", "STATUS"
        ]
    },
    "Overview Box": {
        "sheets": ["DOMESTIK", "INTERNATIONAL"],
        "columns": ["YEAR", "MONTH", "VESSEL OPERATOR", "LOP", "BOX", "BOXES", "TEUS", "DATE"]
    }
}


def get_schema(dataset_name: str, db_schema: Optional[Dict] = None) -> Dict:
    """
    Get schema for a dataset, merging DB schema with static fallback.
    """
    # If db_schema is provided and not empty, use it
    if db_schema:
        sheets = list(db_schema.keys())
        columns = []
        seen = set()
        for sheet_columns in db_schema.values():
            for col in sheet_columns:
                if col not in seen:
                    columns.append(col)
                    seen.add(col)
        # Merge with known columns if available
        static = SCHEMA_REGISTRY.get(dataset_name, {})
        for col in static.get("columns", []):
            if col not in seen:
                columns.append(col)
                seen.add(col)
        return {"sheets": sheets, "columns": columns}
    
    # Fallback to static registry
    if dataset_name in SCHEMA_REGISTRY:
        return SCHEMA_REGISTRY[dataset_name]
    
    return {}


def validate_column(column: Optional[str], dataset: str, db_schema: Optional[Dict] = None) -> bool:
    """
    Check if a column exists in the dataset schema (case-insensitive) or matches valid aliases/temporal columns.
    """
    if column is None:
        return True
        
    schema = get_schema(dataset, db_schema)
    if not schema:
        return True
    
    columns = schema.get("columns", [])
    column_lower = column.lower().strip()
    
    # 1. Direct match
    if any(col.lower().strip() == column_lower for col in columns):
        return True
        
    # 2. Virtual temporal column validation (if dataset has timestamp/date columns)
    if column_lower in ["year", "tahun"]:
        date_keywords = ["year", "tahun", "timestamp", "date", "tanggal", "tanggal surat jawaban tps"]
        if any(any(d in col.lower() for d in date_keywords) for col in columns):
            return True
            
    if column_lower in ["month", "bulan"]:
        date_keywords = ["month", "bulan", "timestamp", "date", "tanggal", "tanggal surat jawaban tps"]
        if any(any(d in col.lower() for d in date_keywords) for col in columns):
            return True

    # 3. Metric aliases
    if column_lower in ["teus", "throughput"]:
        if any("teus" in col.lower() or "throughput" in col.lower() or col.lower() in ["actual", "boxes", "box"] for col in columns):
            return True
            
    if column_lower in ["revenue", "total revenue", "total all revenue"]:
        if any("revenue" in col.lower() or "nominal" in col.lower() for col in columns):
            return True

    if column_lower in ["lop", "vessel operator", "operator"]:
        if any(col.lower() in ["lop", "vessel operator", "operator", "nama perusahaan", "customer"] for col in columns):
            return True

    return False


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
