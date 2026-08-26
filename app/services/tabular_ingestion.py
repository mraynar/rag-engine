import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import text

from app.services.db import get_db_conn
from app.services.googledrive_fetcher import download_googledrive_file
from app.services.sharepoint_fetcher import download_sharepoint_file


def sync_tabular_source(category_name: str, source_url: str, source_type: str) -> dict:
    """Download, parse, and synchronize a tabular spreadsheet source into Supabase.

    Returns the updated source metadata dict.
    """
    # 1. Upsert / get the data_source entry
    with get_db_conn() as conn:
        with conn.begin():
            # Check if exists
            res = conn.execute(
                text("SELECT id FROM data_sources WHERE category_name = :category_name"),
                {"category_name": category_name}
            ).fetchone()

            if res:
                source_id = res[0]
                # Update status to syncing
                conn.execute(
                    text("""
                        UPDATE data_sources
                        SET source_url = :source_url, source_type = :source_type, sync_status = 'syncing', updated_at = now()
                        WHERE id = :source_id
                    """),
                    {"source_url": source_url, "source_type": source_type, "source_id": source_id}
                )
            else:
                # Insert new
                source_id = conn.execute(
                    text("""
                        INSERT INTO data_sources (category_name, source_url, source_type, sync_status)
                        VALUES (:category_name, :source_url, :source_type, 'syncing')
                        RETURNING id
                    """),
                    {"category_name": category_name, "source_url": source_url, "source_type": source_type}
                ).fetchone()[0]

    # 2. Start the fetch and ingestion process
    url = source_url.strip()
    is_gdrive = "drive.google.com" in url or "docs.google.com" in url

    safe_category = category_name.replace(" ", "_").replace("/", "_")
    suffix = ".csv" if "csv" in url.lower() else ".xlsx"
    temp_filename = f"{safe_category}{suffix}"

    fetch_method = "unknown"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / temp_filename

            print(f"[sync_tabular_source] Starting fetch/download for '{category_name}'...")
            # Download using existing fetchers
            if is_gdrive:
                fetch_method = download_googledrive_file(source_url, temp_path)
            else:
                fetch_method = download_sharepoint_file(source_url, temp_path)

            print(f"[sync_tabular_source] Download complete via {fetch_method}. File size: {temp_path.stat().st_size if temp_path.exists() else 0} bytes. Parsing Excel/CSV...")
            # Parse to pandas DataFrame per sheet
            if suffix == ".xlsx":
                xls = pd.read_excel(str(temp_path), sheet_name=None)
            else:
                # Fallback to CSV parsing with encoding checks
                df_csv = None
                for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                    try:
                        df_csv = pd.read_csv(str(temp_path), encoding=enc)
                        break
                    except Exception:
                        continue
                if df_csv is None:
                    raise ValueError("Failed to parse CSV file with standard encodings.")
                print(f"[sync_tabular_source] Parsing complete. Sheets found: {list(xls.keys())}")
            # ── Sanitize each sheet then combine into one wide DataFrame ─────────
            sanitized_dfs = []
            for sheet_name, df in xls.items():
                before = df.shape[0]
                # 1. Normalize column names: strip whitespace + UPPERCASE
                df.columns = [str(col).strip().upper() for col in df.columns]
                # 2. Drop rows where ALL columns are NaN/empty
                df = df.dropna(how='all')
                # 3. Drop fully duplicate rows
                df = df.drop_duplicates()
                after = df.shape[0]
                print(f"[sync_tabular_source] Sheet '{sheet_name}': {before} → {after} rows after sanitize.")
                # 4. Tag each row with its origin sheet (preserved as _sheet column)
                df = df.copy()
                df.insert(0, '_sheet', sheet_name)
                sanitized_dfs.append(df)

            # Concatenate all sheets into one wide flat DataFrame
            if not sanitized_dfs:
                raise ValueError("No data found in any sheet after sanitization.")
            combined_df = pd.concat(sanitized_dfs, axis=0, ignore_index=True)
            print(f"[sync_tabular_source] Combined wide DataFrame: {combined_df.shape[0]} rows × {combined_df.shape[1]} cols.")

            # Build union column schema (all columns across all sheets)
            all_cols = [c for c in combined_df.columns if c != '_sheet']
            column_schema = {"_all_sheets": all_cols}
            # Also preserve per-sheet schema for reference
            for df_sheet in sanitized_dfs:
                sname = df_sheet['_sheet'].iloc[0] if not df_sheet.empty else 'unknown'
                column_schema[sname] = [c for c in df_sheet.columns if c != '_sheet']

            # Serialize combined DataFrame to insert records
            total_rows = 0
            all_row_inserts = []
            for idx, row in combined_df.iterrows():
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

                all_row_inserts.append({
                    "source_id": str(source_id),
                    "sheet_name": clean_record.get('_sheet', 'combined'),
                    "row_index": total_rows,
                    "row_data": json.dumps(clean_record)
                })
                total_rows += 1

            # Perform DB transaction
            with get_db_conn() as conn:
                with conn.begin():
                    print(f"[sync_tabular_source] Connected. Deleting old rows for source_id={source_id}...")
                    # Delete old rows
                    conn.execute(
                        text("DELETE FROM data_rows WHERE source_id = :source_id"),
                        {"source_id": source_id}
                    )

                    # Bulk insert row data
                    dialect_name = conn.dialect.name
                    if dialect_name == "postgresql":
                        from psycopg2.extras import execute_values
                        dbapi_conn = conn.connection.dbapi_connection
                        cursor = dbapi_conn.cursor()

                        query = """
                            INSERT INTO data_rows (source_id, sheet_name, row_index, row_data)
                            VALUES %s
                        """
                        # Convert list of dicts to list of tuples
                        tuples = [(x["source_id"], x["sheet_name"], x["row_index"], x["row_data"]) for x in all_row_inserts]

                        batch_size = 1000
                        total_batches = (len(tuples) - 1) // batch_size + 1
                        print(f"[sync_tabular_source] Inserting {len(tuples)} records in {total_batches} batches using execute_values fast-path...")
                        for i in range(0, len(tuples), batch_size):
                            batch = tuples[i : i + batch_size]
                            current_batch = i // batch_size + 1
                            print(f"[sync_tabular_source] Inserting batch {current_batch}/{total_batches}...")
                            execute_values(cursor, query, batch)
                        cursor.close()
                    else:
                        batch_size = 500
                        insert_stmt = text("""
                            INSERT INTO data_rows (source_id, sheet_name, row_index, row_data)
                            VALUES (:source_id, :sheet_name, :row_index, :row_data)
                        """)
                        total_batches = (len(all_row_inserts) - 1) // batch_size + 1
                        print(f"[sync_tabular_source] Inserting {len(all_row_inserts)} records in {total_batches} batches using fallback insert...")
                        for i in range(0, len(all_row_inserts), batch_size):
                            batch = all_row_inserts[i : i + batch_size]
                            current_batch = i // batch_size + 1
                            print(f"[sync_tabular_source] Inserting batch {current_batch}/{total_batches}...")
                            conn.execute(insert_stmt, batch)
                    print("[sync_tabular_source] All rows inserted successfully.")

                    # Update status to success
                    conn.execute(
                        text("""
                            UPDATE data_sources
                            SET column_schema = :column_schema,
                                row_count = :row_count,
                                sync_status = 'success',
                                last_synced_at = :last_synced_at,
                                fetch_method = :fetch_method,
                                last_error = NULL,
                                updated_at = now()
                            WHERE id = :source_id
                        """),
                        {
                            "column_schema": json.dumps(column_schema),
                            "row_count": total_rows,
                            "last_synced_at": datetime.now(timezone.utc),
                            "fetch_method": fetch_method,
                            "source_id": source_id
                        }
                    )

            # Retrieve final entry
            with get_db_conn() as conn:
                res = conn.execute(
                    text("SELECT * FROM data_sources WHERE id = :source_id"),
                    {"source_id": source_id}
                ).mappings().fetchone()
                return dict(res)

    except Exception as e:
        error_msg = str(e)
        # Mark as failed in database
        with get_db_conn() as conn:
            with conn.begin():
                conn.execute(
                    text("""
                        UPDATE data_sources
                        SET sync_status = 'failed', last_error = :last_error, updated_at = now()
                        WHERE id = :source_id
                    """),
                    {"last_error": error_msg, "source_id": source_id}
                )
        raise RuntimeError(f"Ingestion failed: {error_msg}")
