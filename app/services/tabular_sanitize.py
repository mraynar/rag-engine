import pandas as pd


def _deduplicate_column_names(column_names: list[str]) -> list[str]:
    counts = {}
    used_names = set()
    unique_names = []
    for column_name in column_names:
        count = counts.get(column_name, 0) + 1
        unique_name = column_name if count == 1 else f"{column_name}_{count}"
        while unique_name in used_names:
            count += 1
            unique_name = f"{column_name}_{count}"
        counts[column_name] = count
        used_names.add(unique_name)
        unique_names.append(unique_name)
    return unique_names


def sanitize_and_combine(xls: dict) -> tuple[pd.DataFrame, dict, dict]:
    """Normalize, sanitize, and combine tabular sheets into one DataFrame."""
    sanitized_dfs = []
    sync_stats = {}

    for sheet_name, df in xls.items():
        before = df.shape[0]
        # Normalize column names.
        df.columns = [str(col).strip().upper() for col in df.columns]
        unique_columns = _deduplicate_column_names(list(df.columns))
        if unique_columns != list(df.columns):
            print(f"[sanitize_and_combine] Sheet '{sheet_name}': found duplicate column names, renamed to keep unique: {unique_columns}")
        df.columns = unique_columns
        # Drop empty rows.
        df = df.dropna(how='all')
        # Drop duplicate rows.
        df = df.drop_duplicates()
        after = df.shape[0]
        sync_stats[sheet_name] = {
            "raw_rows": before,
            "final_rows": after,
            "dropped_rows": before - after,
        }
        print(f"[sync_tabular_source] Sheet '{sheet_name}': {before} → {after} rows after sanitize.")
        # Tag rows with their source sheet.
        df = df.copy()
        df.insert(0, '_sheet', sheet_name)
        sanitized_dfs.append(df)

    if not sanitized_dfs:
        raise ValueError("No data found in any sheet after sanitization.")

    combined_df = pd.concat(sanitized_dfs, axis=0, ignore_index=True)

    # Build the union column schema.
    all_cols = [c for c in combined_df.columns if c != '_sheet']
    column_schema = {"_all_sheets": all_cols}
    for df_sheet in sanitized_dfs:
        sname = df_sheet['_sheet'].iloc[0] if not df_sheet.empty else 'unknown'
        column_schema[sname] = [c for c in df_sheet.columns if c != '_sheet']

    return combined_df, column_schema, sync_stats


def _dataframe_to_clean_records_legacy(combined_df: pd.DataFrame) -> list[dict]:
    """Serialize a DataFrame into a list of dict records without DB-specific metadata."""
    clean_records = []
    for _, row in combined_df.iterrows():
        clean_record = {}
        for k, v in row.items():
            try:
                is_null = pd.isnull(v)
            except (TypeError, ValueError):
                is_null = False
            if is_null:
                v_clean = None
            elif hasattr(v, 'isoformat'):
                v_clean = v.isoformat()
            elif hasattr(v, 'item'):
                try:
                    v_clean = v.item()
                except Exception:
                    v_clean = str(v)
            else:
                v_clean = v
            clean_record[str(k)] = v_clean
        clean_records.append(clean_record)

    return clean_records


def dataframe_to_clean_records(combined_df: pd.DataFrame) -> list[dict]:
    """Serialize a DataFrame into clean records using vectorized operations."""
    try:
        clean_df = combined_df.copy()

        def serialize_value(value):
            try:
                is_null = pd.isnull(value)
            except (TypeError, ValueError):
                is_null = False
            if is_null:
                return None
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            if hasattr(value, 'item'):
                try:
                    return value.item()
                except Exception:
                    return str(value)
            return value

        for column_name in clean_df.columns:
            serialized = clean_df[column_name].astype(object).apply(serialize_value)
            clean_df[column_name] = pd.Series(
                serialized.tolist(), index=serialized.index, dtype=object
            ).where(lambda series: pd.notna(series), None)

        records = clean_df.to_dict(orient="records")
    except Exception as error:
        print(f"[dataframe_to_clean_records] Fast path failed, falling back to legacy: {error}")
        return _dataframe_to_clean_records_legacy(combined_df)

    # TODO: remove legacy comparison once confirmed stable over N production syncs
    legacy_records = _dataframe_to_clean_records_legacy(combined_df)
    if records != legacy_records:
        for row_index, (record, legacy_record) in enumerate(zip(records, legacy_records)):
            if record != legacy_record:
                columns = set(record) | set(legacy_record)
                for column_name in columns:
                    if record.get(column_name) != legacy_record.get(column_name):
                        raise RuntimeError(
                            f"Record serialization mismatch at row {row_index}, column '{column_name}': "
                            f"new={record.get(column_name)!r}, legacy={legacy_record.get(column_name)!r}"
                        )
        raise RuntimeError("Record serialization mismatch: different record counts")
    return records
