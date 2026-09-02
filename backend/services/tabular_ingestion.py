import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import text

from backend.services.db import get_db_conn
from backend.services.cloud_fetchers import download_googledrive_file, download_sharepoint_file
from backend.services.tabular_sanitize import sanitize_and_combine, dataframe_to_clean_records


def fetch_and_parse_source(source_url: str, category_name: str) -> tuple[dict, str]:
    """Download and parse a tabular source into a dict of {sheet_name: DataFrame}.
    Returns (xls, fetch_method). Raises ValueError on download/parse failure.
    """
    url = source_url.strip()
    is_gdrive = "drive.google.com" in url or "docs.google.com" in url

    safe_category = category_name.replace(" ", "_").replace("/", "_")
    suffix = ".csv" if "csv" in url.lower() else ".xlsx"
    temp_filename = f"{safe_category}{suffix}"

    fetch_method = "unknown"
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir) / temp_filename

        print(f"[sync_tabular_source] Starting fetch/download for '{category_name}'...")
        if is_gdrive:
            fetch_method = download_googledrive_file(source_url, temp_path)
        else:
            fetch_method = download_sharepoint_file(source_url, temp_path)

        print(f"[sync_tabular_source] Download complete via {fetch_method}. File size: {temp_path.stat().st_size if temp_path.exists() else 0} bytes. Parsing Excel/CSV...")
        if suffix == ".xlsx":
            try:
                xls = pd.read_excel(str(temp_path), sheet_name=None, engine="calamine")
                print("[sync_tabular_source] Parsed Excel with calamine engine.")
            except Exception as calamine_error:
                print(f"[sync_tabular_source] Calamine parsing failed ({calamine_error}); falling back to default Excel engine.")
                xls = pd.read_excel(str(temp_path), sheet_name=None)
        else:
            # Try common encodings for CSV files.
            df_csv = None
            for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
                try:
                    df_csv = pd.read_csv(str(temp_path), encoding=enc)
                    break
                except Exception:
                    continue
            if df_csv is None:
                raise ValueError("Failed to parse CSV file with standard encodings.")
            xls = {"Sheet1": df_csv}

        print(f"[sync_tabular_source] Parsing complete. Sheets found: {list(xls.keys())}")
        return xls, fetch_method


def sync_tabular_source(category_name: str, source_url: str, source_type: str) -> dict:
    """Download, parse, and synchronize a tabular spreadsheet source into Supabase.

    Returns the updated source metadata dict.
    """
    # Create or update the data source entry.
    with get_db_conn() as conn:
        with conn.begin():
            res = conn.execute(
                text("SELECT id FROM data_sources WHERE category_name = :category_name"),
                {"category_name": category_name}
            ).fetchone()

            if res:
                source_id = res[0]
                conn.execute(
                    text("""
                        UPDATE data_sources
                        SET source_url = :source_url, source_type = :source_type, sync_status = 'syncing', updated_at = now()
                        WHERE id = :source_id
                    """),
                    {"source_url": source_url, "source_type": source_type, "source_id": source_id}
                )
            else:
                source_id = conn.execute(
                    text("""
                        INSERT INTO data_sources (category_name, source_url, source_type, sync_status)
                        VALUES (:category_name, :source_url, :source_type, 'syncing')
                        RETURNING id
                    """),
                    {"category_name": category_name, "source_url": source_url, "source_type": source_type}
                ).fetchone()[0]

    try:
        xls, fetch_method = fetch_and_parse_source(source_url, category_name)
        combined_df, column_schema, sync_stats = sanitize_and_combine(xls)
        print(f"[sync_tabular_source] Combined wide DataFrame: {combined_df.shape[0]} rows × {combined_df.shape[1]} cols.")

        total_rows = 0
        all_row_inserts = []
        clean_records = dataframe_to_clean_records(combined_df)
        for clean_record in clean_records:
            all_row_inserts.append({
                "source_id": str(source_id),
                "sheet_name": clean_record.get('_sheet', 'combined'),
                "row_index": total_rows,
                "row_data": json.dumps(clean_record)
            })
            total_rows += 1

        with get_db_conn() as conn:
            with conn.begin():
                print(f"[sync_tabular_source] Connected. Deleting old rows for source_id={source_id}...")
                conn.execute(
                    text("DELETE FROM data_rows WHERE source_id = :source_id"),
                    {"source_id": source_id}
                )

                dialect_name = conn.dialect.name
                if dialect_name == "postgresql":
                    from psycopg2.extras import execute_values
                    dbapi_conn = conn.connection.dbapi_connection
                    cursor = dbapi_conn.cursor()

                    query = """
                        INSERT INTO data_rows (source_id, sheet_name, row_index, row_data)
                        VALUES %s
                    """
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

                from backend.services.tabular.executor import clear_dataframe_cache
                clear_dataframe_cache(source_id)

                actual_count = conn.execute(
                    text("SELECT COUNT(*) FROM data_rows WHERE source_id = :source_id"),
                    {"source_id": source_id}
                ).scalar()
                if actual_count != total_rows:
                    raise RuntimeError(
                        f"Row count mismatch after insert: expected {total_rows}, found {actual_count} in data_rows for source_id={source_id}"
                    )

                sync_stats_exists = conn.execute(
                    text("""
                                                        SELECT EXISTS (
                                                                SELECT 1
                                                                FROM pg_attribute
                                                                WHERE attrelid = to_regclass('data_sources')
                                                                    AND attname = 'sync_stats'
                                                                    AND NOT attisdropped
                                                        )
                    """)
                                        ).scalar() is True

                update_params = {
                    "column_schema": json.dumps(column_schema),
                    "row_count": actual_count,
                    "last_synced_at": datetime.now(timezone.utc),
                    "fetch_method": fetch_method,
                    "source_id": source_id
                }

                if sync_stats_exists:
                    update_sql = text("""
                        UPDATE data_sources
                        SET column_schema = :column_schema,
                            row_count = :row_count,
                            sync_stats = :sync_stats,
                            sync_status = 'success',
                            last_synced_at = :last_synced_at,
                            fetch_method = :fetch_method,
                            last_error = NULL,
                            updated_at = now()
                        WHERE id = :source_id
                    """)
                    update_params["sync_stats"] = json.dumps(sync_stats)
                else:
                    update_sql = text("""
                        UPDATE data_sources
                        SET column_schema = :column_schema,
                            row_count = :row_count,
                            sync_status = 'success',
                            last_synced_at = :last_synced_at,
                            fetch_method = :fetch_method,
                            last_error = NULL,
                            updated_at = now()
                        WHERE id = :source_id
                    """)

                conn.execute(update_sql, update_params)

        with get_db_conn() as conn:
            res = conn.execute(
                text("SELECT * FROM data_sources WHERE id = :source_id"),
                {"source_id": source_id}
            ).mappings().fetchone()
            return dict(res)

    except Exception as e:
        error_msg = str(e)
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
