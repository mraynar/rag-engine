import pandas as pd
import numpy as np

def sanitize_and_combine(xls: dict) -> tuple[pd.DataFrame, dict, dict]:
    """
    Sanitize each DataFrame in xls (dict of {sheet_name: DataFrame}) and combine them into a single wide DataFrame.
    Returns:
      combined_df: pd.DataFrame with '_sheet' column added.
      column_schema: dict of {sheet_name: [list of column names]}
      sync_stats: dict of {sheet_name: row_count}
    """
    combined_dfs = []
    column_schema = {}
    sync_stats = {}

    for sheet_name, df in xls.items():
        if df is None or df.empty:
            continue
        
        # Make a copy to avoid mutating caller data
        sheet_df = df.copy()
        
        # Clean column names
        sheet_df.columns = [str(col).strip() for col in sheet_df.columns]
        
        # Track schema and stats
        column_schema[sheet_name] = [c for c in sheet_df.columns if not c.startswith('_')]
        sync_stats[sheet_name] = len(sheet_df)

        # Attach sheet origin
        sheet_df['_sheet'] = sheet_name
        combined_dfs.append(sheet_df)

    if combined_dfs:
        combined_df = pd.concat(combined_dfs, ignore_index=True)
    else:
        combined_df = pd.DataFrame(columns=['_sheet'])

    return combined_df, column_schema, sync_stats


from datetime import date, datetime

def dataframe_to_clean_records(df: pd.DataFrame) -> list[dict]:
    """
    Convert a DataFrame into a list of clean dict records suitable for JSON storage.
    NaN, NaT, and infinity values are safely converted to None.
    All datetime and date objects are converted to ISO formatted strings.
    """
    if df.empty:
        return []

    # Replace inf and NaN with None
    clean_df = df.replace([np.inf, -np.inf], np.nan)
    records = clean_df.to_dict(orient='records')

    clean_records = []
    for record in records:
        clean_rec = {}
        for key, val in record.items():
            if pd.isna(val):
                clean_rec[key] = None
            elif isinstance(val, (datetime, date, pd.Timestamp, pd.Timedelta)):
                clean_rec[key] = val.isoformat() if hasattr(val, 'isoformat') else str(val)
            elif isinstance(val, (np.integer, np.floating)):
                clean_rec[key] = val.item()
            elif isinstance(val, (np.ndarray, list)):
                clean_rec[key] = str(val)
            else:
                try:
                    # Test JSON serialization safety
                    json.dumps(val)
                    clean_rec[key] = val
                except Exception:
                    clean_rec[key] = str(val)
        clean_records.append(clean_rec)

    return clean_records

