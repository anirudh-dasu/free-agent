"""
File downloader — saves remote files to /tmp/agent_downloads/.
Use run_python to process the downloaded file.
"""
import os
import re
import urllib.parse
import requests

DOWNLOAD_DIR = "/tmp/agent_downloads"
MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def download_file(url: str) -> str:
    """
    Download a file from url into /tmp/agent_downloads/.
    Returns the local file path.
    Raises an exception if the file exceeds 50 MB or the request fails.
    """
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Derive a safe filename from the URL path
    path = urllib.parse.urlparse(url).path
    raw_name = os.path.basename(path) or "download"
    safe_name = re.sub(r"[^\w.\-]", "_", raw_name)[:128]
    local_path = os.path.join(DOWNLOAD_DIR, safe_name)

    resp = requests.get(url, stream=True, timeout=30, headers={"User-Agent": "wintermute/1.0"})
    resp.raise_for_status()

    # Check Content-Length if present
    content_length = resp.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_BYTES:
        raise ValueError(f"File too large: {int(content_length) // (1024*1024)} MB (limit 50 MB)")

    downloaded = 0
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            downloaded += len(chunk)
            if downloaded > MAX_BYTES:
                raise ValueError("File exceeded 50 MB limit during download.")
            f.write(chunk)

    return local_path


from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "download_file",
    "description": (
        "Download a file from a URL to /tmp/agent_downloads/. "
        "Returns the local file path. Use run_python to process the file afterward. "
        "50 MB size limit."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The URL of the file to download"},
        },
        "required": ["url"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    return f"File downloaded to: {download_file(inputs['url'])}", False
