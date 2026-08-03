import re
import requests
from pathlib import Path

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
    # Check warning cookie
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            return value
    # Check page body warning link/token
    match = re.search(r'confirm=([0-9a-zA-Z_]+)', response.text)
    if match:
        return match.group(1)
    return None


def download_googledrive_file(share_url: str, dest_path: Path) -> str:
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
            # Extract SPREADSHEET_ID
            match = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url_str)
            if not match:
                raise ValueError("Gagal mengekstrak ID Spreadsheet dari URL Google Sheets.")
            spreadsheet_id = match.group(1)
            
            download_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
            response = session.get(download_url, stream=True, timeout=60)
            fetch_method = "google_sheets"
        else:
            # Google Drive File logic
            file_id = extract_google_drive_id(url_str)
            download_url = "https://docs.google.com/uc?export=download"
            response = session.get(download_url, params={"id": file_id}, stream=True, timeout=60)
            
            confirm_token = get_confirm_token(response)
            if confirm_token:
                response = session.get(
                    download_url, 
                    params={"id": file_id, "confirm": confirm_token}, 
                    stream=True, 
                    timeout=60
                )
            fetch_method = "google_drive"
            
        if response.status_code != 200:
            raise ValueError(f"Gagal mendownload dari Google, status: {response.status_code}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        # Validate that the downloaded file is a valid Excel spreadsheet
        import pandas as pd
        try:
            # Default behavior loads first sheet
            pd.read_excel(str(dest_path), nrows=1)
        except Exception as e:
            dest_path.unlink(missing_ok=True)
            raise ValueError(
                "Gagal memuat file Excel dari Google. Pastikan file di Google Drive/Sheets tersebut "
                "diatur dengan izin akses publik (Anyone with the link / Siapa saja dengan link)."
            )
            
        return fetch_method
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Jalur Google gagal mengunduh data: {str(e)}")
