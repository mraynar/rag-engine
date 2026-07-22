from fastapi import APIRouter, HTTPException

from app.schemas.config import ConfigCreateRequest, ConfigUpdateRequest
from app.services.config_store import (
    create_config,
    delete_config,
    list_config,
    reveal_config,
    set_active,
    update_config,
)

router = APIRouter()

_RESTART_NOTICE = " Restart server untuk menerapkan perubahan pada konfigurasi rahasia."


# ---------------------------------------------------------------------------
# GET /config — list all entries
# ---------------------------------------------------------------------------

@router.get("/config")
def get_all_config() -> list:
    """Lihat semua entri config (value yang is_secret otomatis disamarkan)."""
    return list_config()


# ---------------------------------------------------------------------------
# POST /config — create a new candidate entry
# ---------------------------------------------------------------------------

@router.post("/config", status_code=201)
def create_config_entry(request: ConfigCreateRequest) -> dict:
    """Tambah kandidat baru di sebuah grup config."""
    new_entry = create_config(
        group=request.group,
        description=request.description,
        value=request.value,
        is_secret=request.is_secret,
    )
    msg = f"Kandidat baru '{new_entry['key']}' berhasil ditambahkan ke grup '{request.group}'."
    if request.is_secret:
        msg += _RESTART_NOTICE
    return {"message": msg, "entry": new_entry}


# ---------------------------------------------------------------------------
# PUT /config/{key} — update description and/or value
# ---------------------------------------------------------------------------

@router.put("/config/{key}")
def update_config_entry(key: str, request: ConfigUpdateRequest) -> dict:
    """Update deskripsi dan/atau nilai dari sebuah entri config.

    CATATAN: perubahan pada nilai gemini_api_key hanya berlaku setelah
    restart server (client Gemini dibuat sekali saat startup).
    """
    if request.description is None and request.value is None:
        raise HTTPException(
            status_code=422,
            detail="Minimal satu field harus diisi: 'description' atau 'value'.",
        )
    try:
        updated = update_config(key, description=request.description, value=request.value)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    msg = f"Config '{key}' berhasil diupdate."
    if updated.get("is_secret"):
        msg += _RESTART_NOTICE
    return {"message": msg, "entry": updated}


# ---------------------------------------------------------------------------
# PATCH /config/{key}/activate — set active candidate in a group
# ---------------------------------------------------------------------------

@router.patch("/config/{key}/activate")
def activate_config_entry(key: str) -> dict:
    """Jadikan entri ini sebagai kandidat aktif di grupnya.

    CATATAN: jika entri yang diaktifkan bersifat rahasia (is_secret),
    perubahan baru berlaku setelah restart server.
    """
    try:
        set_active(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Re-read to check is_secret on the just-activated entry
    from app.services.config_store import _load_store, _find_by_key
    store = _load_store()
    entry = _find_by_key(store, key)

    msg = f"Entri '{key}' kini aktif di grupnya."
    if entry and entry.get("is_secret"):
        msg += _RESTART_NOTICE
    return {"message": msg}


# ---------------------------------------------------------------------------
# DELETE /config/{key} — remove a candidate entry
# ---------------------------------------------------------------------------

@router.delete("/config/{key}")
def delete_config_entry(key: str) -> dict:
    """Hapus sebuah entri config.

    Tidak bisa menghapus entri terakhir di sebuah grup.
    Jika entri yang dihapus adalah yang aktif, entri pertama yang tersisa
    di grup yang sama otomatis dipromosikan menjadi aktif.
    """
    try:
        result = delete_config(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if result["promoted_key"]:
        msg = (
            f"Config '{key}' berhasil dihapus. "
            f"Entri aktif otomatis dialihkan ke: \"{result['promoted_label']}\"."
        )
    else:
        msg = f"Config '{key}' berhasil dihapus."

    return {"message": msg, "promoted_key": result["promoted_key"]}


# ---------------------------------------------------------------------------
# GET /config/{key}/reveal — reveal real value of an entry
# ---------------------------------------------------------------------------

@router.get("/config/{key}/reveal")
def get_revealed_config(key: str) -> dict:
    """Ambil nilai asli (unmasked) dari sebuah entri config (biasanya untuk rahasia)."""
    try:
        val = reveal_config(key)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"value": val}

