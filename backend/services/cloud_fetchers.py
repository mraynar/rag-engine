"""
Layanan pengunduhan file spreadsheet dari cloud storage (Google Drive & SharePoint/OneDrive).
"""
import base64
import json
import re
from pathlib import Path
import requests
import pandas as pd

from backend.services.stores import get_active_value


# ── Google Drive & Google Sheets Fetcher ──────────────────────────────────────

def extract_google_drive_id(url: str) -> str:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"id=([a-zA-Z0-9_-]+)",
        r"/spreadsheets/d/([a-zA-Z0-9_-]+)",
        r"/document/d/([a-zA-Z0-9_-]+)",
        r"/presentation/d/([a-zA-Z0-9_-]+)"
    ]
    for p in patterns:
        match = re.search(p, url)
        if match:
            return match.group(1)
    raise ValueError("Link Google Drive tidak valid. Pastikan link mengandung ID file (contoh: drive.google.com/file/d/ID/view).")


def get_confirm_token(response) -> str:
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    match = re.search(r'confirm=([0-9a-zA-Z_]+)', response.text)
    if match:
        return match.group(1)
    return None


def download_googledrive_file(share_url: str, dest_path: Path) -> str:
    """Mengunduh file Excel dari link Google Drive atau Google Sheets."""
    url_str = share_url.strip()
    is_sheets = "docs.google.com" in url_str and "/spreadsheets/d/" in url_str
    is_drive_file = "drive.google.com" in url_str and ("/file/d/" in url_str or "id=" in url_str)
    
    if not is_sheets and not is_drive_file:
        raise ValueError(
            "Format link Google tidak dikenali. Gunakan link file Google Drive "
            "(drive.google.com/file/d/...) atau Google Sheets (docs.google.com/spreadsheets/d/...)"
        )
        
    session = requests.Session()
    try:
        if is_sheets:
            match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url_str)
            if not match:
                raise ValueError("Gagal mengekstrak ID Spreadsheet dari URL Google Sheets.")
            spreadsheet_id = match.group(1)
            download_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
            response = session.get(download_url, stream=True, timeout=60)
            fetch_method = "google_sheets"
        else:
            file_id = extract_google_drive_id(url_str)
            download_url = "https://docs.google.com/uc?export=download"
            response = session.get(download_url, params={"id": file_id}, stream=True, timeout=60)
            confirm_token = get_confirm_token(response)
            if confirm_token:
                response = session.get(download_url, params={"id": file_id, "confirm": confirm_token}, stream=True, timeout=60)
            fetch_method = "google_drive"
            
        if response.status_code != 200:
            raise ValueError(f"Gagal mendownload dari Google, status: {response.status_code}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        try:
            pd.read_excel(str(dest_path), nrows=1)
        except Exception:
            dest_path.unlink(missing_ok=True)
            raise ValueError("Gagal memuat file Excel dari Google. Pastikan izin akses diatur ke 'Anyone with the link'.")
            
        return fetch_method
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Jalur Google gagal mengunduh data: {str(e)}")


# ── Microsoft SharePoint & OneDrive Fetcher ───────────────────────────────────

def get_azure_credentials() -> dict:
    try:
        val = get_active_value("azure_graph")
        creds = json.loads(val)
        if not creds.get("tenant_id") or not creds.get("client_id") or not creds.get("client_secret"):
            raise ValueError()
        return creds
    except Exception:
        raise ValueError("Kredensial Azure/Graph API belum dikonfigurasi.")


def get_graph_access_token() -> str:
    creds = get_azure_credentials()
    token_url = f"https://login.microsoftonline.com/{creds['tenant_id']}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "scope": "https://graph.microsoft.com/.default"
    }
    res = requests.post(token_url, data=payload, timeout=15)
    if res.status_code != 200:
        raise ValueError(f"Autentikasi Azure Graph gagal: {res.json().get('error_description', res.text)}")
    return res.json()["access_token"]


def resolve_share_url_to_drive_item(share_url: str, access_token: str) -> dict:
    base64_url = base64.urlsafe_b64encode(share_url.strip().encode('utf-8')).decode('utf-8')
    sharing_token = f"u!{base64_url.rstrip('=')}"
    graph_url = f"https://graph.microsoft.com/v1.0/shares/{sharing_token}/driveItem"
    headers = {"Authorization": f"Bearer {access_token}"}
    res = requests.get(graph_url, headers=headers, timeout=20)
    if res.status_code in (403, 404):
        raise ValueError("Link tidak bisa diakses — gunakan tombol Share/Copy Link di SharePoint.")
    elif res.status_code != 200:
        raise ValueError(f"Gagal me-resolve link sharepoint: {res.text}")
    return res.json()


def has_valid_azure_credentials() -> bool:
    try:
        creds = get_azure_credentials()
        return bool(creds.get("tenant_id") and creds.get("client_id") and creds.get("client_secret"))
    except Exception:
        return False


def download_sharepoint_file(share_url: str, dest_path: Path) -> str:
    """Mengunduh file Excel dari link Microsoft SharePoint atau OneDrive."""
    use_graph = has_valid_azure_credentials()
    if use_graph:
        access_token = get_graph_access_token()
        drive_item = resolve_share_url_to_drive_item(share_url, access_token)
        download_url = drive_item.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise ValueError("Gagal mendapatkan link download dari Microsoft Graph API.")

        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(download_url, headers=headers, timeout=60, stream=True)
        if response.status_code != 200:
            raise ValueError(f"Gagal mengunduh file dari Graph API, status: {response.status_code}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        try:
            pd.read_excel(str(dest_path), nrows=1)
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            raise ValueError(f"File terunduh bukan spreadsheet Excel (.xlsx) yang valid: {str(e)}")
        return "graph_api"
    else:
        if "e=" not in share_url:
            raise ValueError("Gunakan link dari tombol Share/Copy Link SharePoint (mengandung token 'e=').")

        fallback_url = share_url
        if "download=1" not in fallback_url:
            separator = "&" if "?" in fallback_url else "?"
            fallback_url = f"{fallback_url}{separator}download=1"

        response = requests.get(fallback_url, allow_redirects=True, timeout=60, stream=True)
        if response.status_code != 200:
            raise ValueError(f"Gagal mengunduh file dari SharePoint, status: {response.status_code}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        try:
            pd.read_excel(str(dest_path), nrows=1)
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            raise ValueError("File terunduh bukan Excel (.xlsx) yang valid.")
        return "fallback_download"
