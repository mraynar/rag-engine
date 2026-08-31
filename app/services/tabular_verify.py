import hashlib
import json

from app.services.db import get_db_conn
from app.services.tabular_sanitize import sanitize_and_combine, dataframe_to_clean_records
from sqlalchemy import text


def verify_source(category_name: str, source_url: str) -> dict:
    """Compare the live source rows against rows currently stored in Postgres."""
    with get_db_conn() as conn:
        source_row = conn.execute(
            text("SELECT id FROM data_sources WHERE category_name = :category_name"),
            {"category_name": category_name}
        ).fetchone()

        if not source_row:
            raise ValueError(f"No synced data found in database for category '{category_name}'. Sync it first.")
        source_id = source_row[0]

    xls, _ = fetch_and_parse_source(source_url, category_name)
    combined_df, _, _ = sanitize_and_combine(xls)
    source_records = dataframe_to_clean_records(combined_df)

    source_hashes = {}
    for record in source_records:
        record_hash = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        source_hashes[record_hash] = record

    with get_db_conn() as conn:
        db_rows = conn.execute(
            text("SELECT row_data FROM data_rows WHERE source_id = :source_id"),
            {"source_id": source_id}
        ).fetchall()

    db_hashes = {}
    for row in db_rows:
        raw = row[0]
        record = json.loads(raw) if isinstance(raw, str) else raw
        record_hash = hashlib.sha256(
            json.dumps(record, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        db_hashes[record_hash] = record

    source_hash_set = set(source_hashes.keys())
    db_hash_set = set(db_hashes.keys())

    missing_in_db = sorted(source_hash_set - db_hash_set)
    stale_in_db = sorted(db_hash_set - source_hash_set)
    matching = sorted(source_hash_set & db_hash_set)

    def sample_records(hash_list: list[str], source_map: dict, fallback_map: dict, limit: int = 5) -> list[dict]:
        sample = []
        for value in hash_list[:limit]:
            sample.append(source_map.get(value, fallback_map.get(value)))
        return sample

    report = {
        "category_name": category_name,
        "source_id": str(source_id),
        "total_rows_in_source": len(source_records),
        "total_rows_in_db": len(db_rows),
        "matching_rows": len(matching),
        "missing_in_db_count": len(missing_in_db),
        "stale_in_db_count": len(stale_in_db),
        "is_in_sync": len(missing_in_db) == 0 and len(stale_in_db) == 0,
        "sample_missing_in_db": sample_records(missing_in_db, source_hashes, db_hashes, 5),
        "sample_stale_in_db": sample_records(stale_in_db, db_hashes, source_hashes, 5),
    }
    return report


from app.services.tabular_ingestion import fetch_and_parse_source
