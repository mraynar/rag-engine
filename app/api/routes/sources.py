import tempfile
from pathlib import Path
from threading import Lock
from fastapi import APIRouter, HTTPException, Depends

_syncing_sources = set()
_sync_lock = Lock()

from app.schemas.source import SourceCreateRequest, SourceUpdateRequest
from app.core.auth import require_user
from app.services.sources_store import (
    list_sources,
    get_source,
    create_source,
    update_source,
    delete_source,
    mark_synced,
    mark_failed,
)
from app.services.sharepoint_fetcher import download_sharepoint_file
from app.services.googledrive_fetcher import download_googledrive_file
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
def get_all_sources(user: dict = Depends(require_user)) -> list:
    return list_sources()


@router.post("", status_code=201)
def create_new_source(request: SourceCreateRequest, user: dict = Depends(require_user)) -> dict:
    try:
        new_entry = create_source(
            category_name=request.category_name,
            onedrive_url=request.onedrive_url,
        )
        return {"message": "Category added successfully.", "source": new_entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}")
def update_existing_source(id: str, request: SourceUpdateRequest, user: dict = Depends(require_user)) -> dict:
    try:
        updated = update_source(
            id=id,
            category_name=request.category_name,
            onedrive_url=request.onedrive_url,
        )
        return {"message": "Category updated successfully.", "source": updated}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{id}")
def delete_existing_source(id: str, user: dict = Depends(require_user)) -> dict:
    try:
        source = get_source(id)
        if source:
            category_name = source["category_name"]
            from app.services.ingestion import delete_category_vector_data
            delete_category_vector_data(category_name)

            # Clean up Supabase Postgres tables as well
            from app.services.db import get_db_conn
            from sqlalchemy import text
            try:
                with get_db_conn() as conn:
                    with conn.begin():
                        conn.execute(
                            text("DELETE FROM data_sources WHERE category_name = :category_name"),
                            {"category_name": category_name}
                        )
            except Exception as e:
                print(f"[sources] Warning: failed to delete '{category_name}' from Supabase: {e}")

        delete_source(id)
        return {"message": "Category deleted successfully."}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id}/sync")
def sync_source(id: str, user: dict = Depends(require_user)) -> dict:
    with _sync_lock:
        if id in _syncing_sources:
            raise HTTPException(
                status_code=409,
                detail="Synchronization for this category is currently in progress."
            )
        _syncing_sources.add(id)

    try:
        source = get_source(id)
        if not source:
            raise HTTPException(status_code=404, detail="Category not found.")

        url = source["onedrive_url"].strip().lower()
        is_gdrive = "drive.google.com" in url or "docs.google.com" in url

        try:
            # Call new zero-AI tabular sync pipeline
            from app.services.tabular_ingestion import sync_tabular_source
            db_source = sync_tabular_source(
                category_name=source["category_name"],
                source_url=source["onedrive_url"],
                source_type="google_sheets" if is_gdrive else "sharepoint"
            )

            chunk_count = db_source.get("row_count", 0)
            fetch_method = db_source.get("fetch_method", "unknown")

            # Keep local sources_store.json in sync for frontend compatibility
            updated = mark_synced(id, chunk_count, fetch_method)
            return {
                "message": f"Synchronization successful. Indexed {chunk_count} rows in Supabase.",
                "source": updated,
            }
        except Exception as e:
            error_msg = str(e)
            mark_failed(id, error_msg)
            raise HTTPException(
                status_code=400,
                detail=f"Synchronization failed: {error_msg}",
            )
    finally:
        with _sync_lock:
            _syncing_sources.discard(id)
