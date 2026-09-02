import chromadb
from fastapi import APIRouter, Form, HTTPException, UploadFile, Depends

from app.core.config import VECTOR_STORE_DIR
from app.core.auth import require_user
from app.schemas.document import DocumentToggleRequest
from app.services.document_store import (
    delete_document,
    list_documents,
    register_document,
    toggle_active,
)
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENTS_DIR_NAME = "documents"


def _get_documents_dir():
    from pathlib import Path
    base = Path(__file__).resolve().parent.parent.parent.parent / "data" / "documents"
    base.mkdir(parents=True, exist_ok=True)
    return base




@router.get("")
def get_documents() -> list:
    """Public: guest users can also see the document list."""
    return list_documents()


@router.patch("/{filename}")
def toggle_document_active(filename: str, request: DocumentToggleRequest, user: dict = Depends(require_user)) -> dict:
    try:
        entry = toggle_active(filename, request.is_active)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    status = "activated" if request.is_active else "deactivated"
    return {"message": f"Document '{filename}' {status}.", "document": entry}


@router.delete("/{filename}")
def delete_document_entry(filename: str, user: dict = Depends(require_user)) -> dict:
    documents_dir = _get_documents_dir()
    file_path = documents_dir / filename

    if file_path.exists():
        file_path.unlink()

    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_or_create_collection(name="tps_docs")
        collection.delete(where={"source": filename})
    except Exception:
        pass  # non-fatal; registry deletion still proceeds

    try:
        delete_document(filename)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"message": f"Document '{filename}' deleted successfully."}


@router.get("/{filename}/preview")
def get_document_preview(filename: str, limit: int = 100, offset: int = 0, user: dict = Depends(require_user)) -> dict:
    """Fetch text chunks stored in ChromaDB for a manual document."""
    try:
        chroma_client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = chroma_client.get_or_create_collection(name="tps_docs")
        
        # Query matching chunks
        results = collection.get(
            where={"source": filename},
            limit=limit,
            offset=offset,
            include=["documents", "metadatas"]
        )
        
        chunks = []
        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        
        for i in range(len(ids)):
            chunks.append({
                "id": ids[i],
                "content": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {}
            })
            
        # Count total matching chunks
        all_results = collection.get(where={"source": filename}, include=[])
        total_chunks = len(all_results.get("ids", []))
        
        return {
            "filename": filename,
            "total_chunks": total_chunks,
            "chunks": chunks,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch ChromaDB preview: {e}")
