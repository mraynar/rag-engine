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


def decode_jwt_payload(token: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) >= 2:
            payload_b64 = parts[1]
            payload_b64 += '=' * (-len(payload_b64) % 4)
            payload_json = base64.b64decode(payload_b64).decode('utf-8')
            import json
            return json.loads(payload_json)
    except Exception as e:
        return {"error": f"Gagal mendecode JWT payload: {str(e)}"}
    return {}


def resolve_share_url_to_drive_item(share_url: str, access_token: str) -> dict:
    # Print original URL
    print("=== DIAGNOSTIC LOG: SHAREPOINT RESOLVE ===", flush=True)
    print(f"Original Share URL: {share_url}", flush=True)

    # URL safe base64 encoding without padding
    base64_url = base64.urlsafe_b64encode(share_url.strip().encode('utf-8')).decode('utf-8')
    sharing_token = f"u!{base64_url.rstrip('=')}"
    print(f"Encoded Share ID: {sharing_token}", flush=True)

    graph_url = f"https://graph.microsoft.com/v1.0/shares/{sharing_token}/driveItem"
    print(f"Full Endpoint URL: {graph_url}", flush=True)

    # Decode access token payload to check permissions
    payload = decode_jwt_payload(access_token)
    print("--- Access Token Diagnostics ---", flush=True)
    print(f"Token Type: Bearer", flush=True)
    print(f"Roles: {payload.get('roles', 'No roles claim found')}", flush=True)
    print(f"Scp (Scopes): {payload.get('scp', 'No scp claim found')}", flush=True)
    print(f"Full Claims Payload (excl. signature): {payload}", flush=True)
    print("--------------------------------", flush=True)

    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        res = requests.get(graph_url, headers=headers, timeout=20)
        print(f"Graph API Response Status Code: {res.status_code}", flush=True)
        print(f"Graph API Response Body: {res.text}", flush=True)
        print("==========================================", flush=True)

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


def has_valid_azure_credentials() -> bool:
    try:
        creds = get_azure_credentials()
        return bool(creds.get("tenant_id") and creds.get("client_id") and creds.get("client_secret"))
    except Exception:
        return False


def download_sharepoint_file(share_url: str, dest_path: Path) -> str:
    """Download SharePoint/OneDrive file. Returns the fetch_method ('graph_api' or 'fallback_download')."""
    use_graph = has_valid_azure_credentials()
    print(f"[sharepoint_fetcher] has_valid_azure_credentials={use_graph}", flush=True)

    if use_graph:
        access_token = get_graph_access_token()
        drive_item = resolve_share_url_to_drive_item(share_url, access_token)

        download_url = drive_item.get("@microsoft.graph.downloadUrl")
        if not download_url:
            raise ValueError("Gagal mendapatkan link download dari Microsoft Graph API metadata.")

        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            response = requests.get(download_url, headers=headers, timeout=60, stream=True)
            if response.status_code != 200:
                raise ValueError(f"Gagal mengunduh file dari Graph API, status: {response.status_code}")

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Validate Excel format
            import pandas as pd
            try:
                pd.read_excel(str(dest_path), nrows=1)
            except Exception as e:
                dest_path.unlink(missing_ok=True)
                raise ValueError(f"File terunduh via Graph API bukan spreadsheet Excel (.xlsx) yang valid: {str(e)}")

            return "graph_api"
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Gagal mengunduh file dari SharePoint: {str(e)}")
    else:
        # TEMPORARY FALLBACK — replace with Graph API once Azure credentials are available
        # Check token parameter in query string
        if "e=" not in share_url:
            raise ValueError(
                "Link ini sepertinya bukan hasil tombol Share/Copy Link (tidak ada token akses 'e='). "
                "Buka file di SharePoint, klik Share > Copy Link, lalu gunakan link itu."
            )

        fallback_url = share_url
        if "download=1" not in fallback_url:
            separator = "&" if "?" in fallback_url else "?"
            fallback_url = f"{fallback_url}{separator}download=1"

        try:
            response = requests.get(fallback_url, allow_redirects=True, timeout=60, stream=True)
            if response.status_code == 403:
                raise ValueError(
                    "Gagal download — Server SharePoint menolak akses (403 Forbidden). "
                    "Link yang Anda masukkan sepertinya bukan 'Share Link' yang benar. "
                    "Cara benar: buka file di SharePoint/OneDrive, klik tombol 'Share', "
                    "pilih 'Copy Link' (bukan salin dari address bar browser), pastikan "
                    "aksesnya 'Anyone with the link', lalu paste link itu di sini."
                )
            elif response.status_code != 200:
                raise ValueError(f"Gagal mengunduh file dari fallback URL, status: {response.status_code}")

            # Check content-type to avoid downloading HTML login page
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                raise ValueError(
                    "Gagal download — kemungkinan link butuh login. "
                    "Coba pastikan link dibuat dengan akses 'Anyone in TPS with the link' (public), "
                    "atau tunggu kredensial Azure siap."
                )

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            # Validate Excel format using pandas
            import pandas as pd
            try:
                pd.read_excel(str(dest_path), nrows=1)
            except Exception as e:
                dest_path.unlink(missing_ok=True)
                raise ValueError(
                    "Gagal download — file terunduh bukan Excel (.xlsx) yang valid (kemungkinan dialihkan ke halaman login). "
                    "Pastikan tipe akses link diatur ke 'Anyone' (siapa saja) atau gunakan kredensial Azure."
                )

            return "fallback_download"
        except Exception as e:
            if isinstance(e, ValueError):
                raise
            raise ValueError(f"Jalur fallback gagal menghubungi OneDrive/SharePoint: {str(e)}")

