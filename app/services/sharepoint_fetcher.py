"""
SharePoint fetcher alias module.
"""
from app.services.cloud_fetchers import (
    get_azure_credentials,
    get_graph_access_token,
    has_valid_azure_credentials,
    download_sharepoint_file,
)

__all__ = [
    "get_azure_credentials",
    "get_graph_access_token",
    "has_valid_azure_credentials",
    "download_sharepoint_file",
]
