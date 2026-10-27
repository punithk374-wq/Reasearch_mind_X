import ipaddress
import socket
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

MAX_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_REDIRECTS = 3
ALLOWED_PORTS = {None, 80, 443}


class DownloadError(Exception):
    """Raised when a PDF cannot be downloaded safely."""


def _check_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise DownloadError("Only http and https links can be imported.")
    if not parsed.hostname:
        raise DownloadError("The link has no host name.")
    if parsed.username or parsed.password:
        raise DownloadError("Links that contain credentials are not allowed.")
    try:
        port = parsed.port
    except ValueError:
        raise DownloadError("The link has an invalid port.")
    if port not in ALLOWED_PORTS:
        raise DownloadError("That port is not allowed.")

    try:
        infos = socket.getaddrinfo(
            parsed.hostname,
            port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        raise DownloadError("Could not find that website.")

    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        # Refuses loopback, private networks, link-local (cloud metadata), reserved
        if not ip.is_global:
            raise DownloadError("That address is not allowed.")


def download_pdf(url: str, dest_dir: Path) -> Path:
    """Download a PDF to dest_dir under a random name, checking every hop."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{uuid.uuid4().hex}.pdf"
    current = url

    try:
        for _ in range(MAX_REDIRECTS + 1):
            _check_url(current)
            try:
                resp = requests.get(
                    current,
                    stream=True,
                    timeout=(10, 20),
                    allow_redirects=False,  # we follow redirects ourselves, re-checking each
                    headers={
                        "User-Agent": "ResearchMindX/1.0 (academic project)",
                        "Accept": "application/pdf,*/*",
                    },
                )
            except requests.RequestException:
                raise DownloadError("Could not download the file.")

            with resp:
                if resp.status_code in (301, 302, 303, 307, 308):
                    location = resp.headers.get("Location")
                    if not location:
                        raise DownloadError("The download redirected nowhere.")
                    current = urljoin(current, location)
                    continue

                if resp.status_code != 200:
                    raise DownloadError(
                        f"The website refused the download ({resp.status_code})."
                    )

                declared = resp.headers.get("Content-Length", "")
                if declared.isdigit() and int(declared) > MAX_BYTES:
                    raise DownloadError("File too large (max 20 MB).")

                size = 0
                first = True
                with open(dest, "wb") as out:
                    for block in resp.iter_content(chunk_size=64 * 1024):
                        if not block:
                            continue
                        if first:
                            if not block.startswith(b"%PDF-"):
                                raise DownloadError(
                                    "That link did not return a PDF file. "
                                    "Try opening the publisher page instead."
                                )
                            first = False
                        size += len(block)
                        if size > MAX_BYTES:
                            raise DownloadError("File too large (max 20 MB).")
                        out.write(block)

                if size == 0:
                    raise DownloadError("The downloaded file was empty.")
                return dest

        raise DownloadError("Too many redirects.")
    except Exception:
        dest.unlink(missing_ok=True)  # never leave a partial file behind
        raise