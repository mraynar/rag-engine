import tempfile
from pathlib import Path
from threading import Lock
from fastapi import APIRouter, HTTPException

_syncing_sources = set()
_sync_lock = Lock()

from app.schemas.source import SourceCreateRequest, SourceUpdateRequest
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
def get_all_sources() -> list:
    return list_sources()


@router.post("", status_code=201)
def create_new_source(request: SourceCreateRequest) -> dict:
    try:
        new_entry = create_source(
            category_name=request.category_name,
            onedrive_url=request.onedrive_url,
        )
        return {"message": "Category added successfully.", "source": new_entry}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{id}")
def update_existing_source(id: str, request: SourceUpdateRequest) -> dict:
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
def delete_existing_source(id: str) -> dict:
    try:
        source = get_source(id)
        if source:
            category_name = source["category_name"]
            from app.services.ingestion import delete_category_vector_data
            delete_category_vector_data(category_name)
        delete_source(id)
        return {"message": "Category deleted successfully."}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{id}/sync")
def sync_source(id: str) -> dict:
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

        safe_category = source["category_name"].replace(" ", "_").replace("/", "_")
        temp_filename = f"{safe_category}.xlsx"

        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / temp_filename
            try:
                if is_gdrive:
                    fetch_method = download_googledrive_file(source["onedrive_url"], temp_path)
                else:
                    fetch_method = download_sharepoint_file(source["onedrive_url"], temp_path)

                chunk_count = ingest_document(
                    file_path=temp_path,
                    filename=temp_filename,
                    category=source["category_name"],
                )

                updated = mark_synced(id, chunk_count, fetch_method)
                return {
                    "message": f"Synchronization successful. Indexed {chunk_count} chunks.",
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
