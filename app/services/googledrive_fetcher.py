"""
Google Drive fetcher alias module.
"""
from app.services.cloud_fetchers import (
    extract_google_drive_id,
    download_googledrive_file,
)

__all__ = ["extract_google_drive_id", "download_googledrive_file"]
