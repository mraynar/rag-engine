import base64
import requests
from pathlib import Path


def convert_onedrive_url(share_url: str) -> str:
    url = share_url.strip()

    if "1drv.ms" in url:
        try:
            res = requests.head(url, allow_redirects=True, timeout=10)
            url = res.url
        except Exception:
            pass

    if "onedrive.live.com" in url or "1drv.ms" in url:
        base64_url = base64.b64encode(url.encode('utf-8')).decode('utf-8')
        encoded_url = base64_url.replace('=', '').replace('/', '_').replace('+', '-')
        return f"https://api.onedrive.com/v1.0/shares/u!{encoded_url}/root/content"

    elif "sharepoint.com" in url:
        if "?" in url:
            base_url = url.split("?")[0]
            params = url.split("?")[1]
            param_list = params.split("&")
            new_params = []
            for p in param_list:
                if p.startswith("web=") or p.startswith("download="):
                    continue
                new_params.append(p)
            new_params.append("download=1")
            return f"{base_url}?{'&'.join(new_params)}"
        else:
            return f"{url}?download=1"

    if "?" in url:
        return f"{url}&download=1"
    return f"{url}?download=1"


def download_onedrive_file(share_url: str, dest_path: Path) -> Path:
    direct_url = convert_onedrive_url(share_url)
    try:
        response = requests.get(direct_url, timeout=30, stream=True)
        if response.status_code in (401, 403):
            raise ValueError(
                "Link OneDrive harus berupa share link publik (Anyone with the link)."
            )
        elif response.status_code != 200:
            raise ValueError(
                f"Gagal mengunduh file dari OneDrive. Status code: {response.status_code}"
            )

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return dest_path
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Gagal menghubungi server OneDrive: {str(e)}")
