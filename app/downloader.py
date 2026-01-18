import asyncio
import os
import re
import urllib.parse
from typing import Optional, Tuple

import aiohttp
import requests
from bs4 import BeautifulSoup

from .config import MAX_DOWNLOAD_MB
from .utils import safe_name

GDRIVE_FILE_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")


def _guess_filename_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    name = os.path.basename(path) or "download"
    return safe_name(urllib.parse.unquote(name))


def is_google_drive(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return "drive.google.com" in host


def is_mediafire(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return "mediafire.com" in host


def normalize_google_drive(url: str) -> Optional[str]:
    """Return a direct download URL if possible."""
    m = GDRIVE_FILE_RE.search(url)
    if m:
        file_id = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    # Some links: https://drive.google.com/open?id=...
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if "id" in q and q["id"]:
        file_id = q["id"][0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return None


def resolve_mediafire_direct(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        # common selector
        a = soup.find("a", {"id": "downloadButton"})
        if a and a.get("href"):
            return a["href"]
        # fallback: first link that looks like a download
        for a in soup.find_all("a"):
            href = a.get("href") or ""
            if "download" in href and href.startswith("http"):
                return href
    except Exception:
        return None
    return None


async def head_content_length(session: aiohttp.ClientSession, url: str) -> Optional[int]:
    try:
        async with session.head(url, allow_redirects=True, timeout=30) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl else None
    except Exception:
        return None


async def download_file(
    url: str,
    dest_path: str,
    progress_cb=None,
    chunk_size: int = 1024 * 256,
) -> Tuple[str, int]:
    """Download URL -> dest_path. Returns (final_path, size_bytes)."""
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    original_url = url
    if is_mediafire(url):
        direct = resolve_mediafire_direct(url)
        if direct:
            url = direct
    if is_google_drive(url):
        direct = normalize_google_drive(url)
        if direct:
            url = direct

    timeout = aiohttp.ClientTimeout(total=None, sock_connect=30, sock_read=300)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        # Google Drive sometimes needs a confirm token for large files
        size_limit_bytes = MAX_DOWNLOAD_MB * 1024 * 1024

        async def _stream(u: str) -> Tuple[bytes, dict]:
            async with session.get(u, allow_redirects=True) as resp:
                resp.raise_for_status()
                # For drive large files, capture cookies for confirm
                data = await resp.read()
                return data, {"cookies": session.cookie_jar.filter_cookies(u)}

        # Try streaming normally (no full read)
        async with session.get(url, allow_redirects=True) as resp:
            resp.raise_for_status()
            # Drive confirm page
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "text/html" in ctype and is_google_drive(original_url):
                html = await resp.text(errors="ignore")
                confirm = re.search(r"confirm=([0-9A-Za-z_]+)", html)
                file_id_match = re.search(r"id=([a-zA-Z0-9_-]+)", url)
                if confirm and file_id_match:
                    confirm_token = confirm.group(1)
                    file_id = file_id_match.group(1)
                    url2 = f"https://drive.google.com/uc?export=download&confirm={confirm_token}&id={file_id}"
                    # restart request
                    return await download_file(url2, dest_path, progress_cb=progress_cb, chunk_size=chunk_size)

            total = resp.headers.get("Content-Length")
            total = int(total) if total else None
            if total and total > size_limit_bytes:
                raise ValueError(f"File too large: {total} bytes (limit {size_limit_bytes})")

            wrote = 0
            tmp_path = dest_path + ".part"
            with open(tmp_path, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if not chunk:
                        continue
                    f.write(chunk)
                    wrote += len(chunk)
                    if wrote > size_limit_bytes:
                        raise ValueError(f"File too large (limit {size_limit_bytes})")
                    if progress_cb:
                        await progress_cb(wrote, total)
            os.replace(tmp_path, dest_path)
            return dest_path, wrote
