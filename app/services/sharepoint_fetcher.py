import base64
import json
import requests
from pathlib import Path
from app.services.config_store import get_active_value


def get_azure_credentials() -> dict:
    try:
        val = get_active_value("azure_graph")
    except Exception:
        raise ValueError(
            "Kredensial Azure/Graph API belum dikonfigurasi. Isi dulu di halaman Konfigurasi > Tata Kelola."
        )

    try:
        creds = json.loads(val)
        tenant_id = creds.get("tenant_id")
        client_id = creds.get("client_id")
        client_secret = creds.get("client_secret")
        if not tenant_id or not client_id or not client_secret:
            raise ValueError()
        return creds
    except Exception:
        raise ValueError(
            "Format kredensial Azure tidak valid atau belum lengkap. "
            "Isi dulu di halaman Konfigurasi > Tata Kelola."
        )


def get_graph_access_token() -> str:
    creds = get_azure_credentials()
    tenant_id = creds["tenant_id"]
    client_id = creds["client_id"]
    client_secret = creds["client_secret"]

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": "https://graph.microsoft.com/.default"
    }

    try:
        res = requests.post(token_url, data=payload, timeout=15)
        if res.status_code != 200:
            raise ValueError(f"Autentikasi Azure Graph gagal: {res.json().get('error_description', res.text)}")
        return res.json()["access_token"]
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Gagal menghubungi server Microsoft login: {str(e)}")


def resolve_share_url_to_drive_item(share_url: str, access_token: str) -> dict:
    # URL safe base64 encoding without padding
    base64_url = base64.urlsafe_b64encode(share_url.strip().encode('utf-8')).decode('utf-8')
    sharing_token = f"u!{base64_url.rstrip('=')}"

    graph_url = f"https://graph.microsoft.com/v1.0/shares/{sharing_token}/driveItem"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        res = requests.get(graph_url, headers=headers, timeout=20)
        if res.status_code in (403, 404):
            raise ValueError(
                "Link tidak bisa diakses — pastikan link dibuat lewat tombol Share/Copy Link di SharePoint, "
                "bukan disalin dari address bar, dan aplikasi Azure sudah punya izin akses ke situs ini."
            )
        elif res.status_code != 200:
            raise ValueError(f"Gagal me-resolve link sharepoint (Microsoft Graph Error: {res.text})")
        return res.json()
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Gagal menghubungi Microsoft Graph API: {str(e)}")


def download_sharepoint_file(share_url: str, dest_path: Path) -> Path:
    access_token = get_graph_access_token()
    drive_item = resolve_share_url_to_drive_item(share_url, access_token)

    download_url = drive_item.get("@microsoft.graph.downloadUrl")
    if not download_url:
        raise ValueError("Gagal mendapatkan link download dari Microsoft Graph API metadata.")

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(download_url, headers=headers, timeout=60, stream=True)
        if response.status_code != 200:
            raise ValueError(f"Gagal mengunduh file, status: {response.status_code}")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return dest_path
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Gagal mengunduh file dari SharePoint: {str(e)}")
