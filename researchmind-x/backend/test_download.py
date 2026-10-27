from app.services.download_service import DownloadError, _check_url

blocked = [
    "http://127.0.0.1/x.pdf",
    "http://localhost/x.pdf",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/x.pdf",
    "http://192.168.1.1/x.pdf",
    "file:///etc/passwd",
    "ftp://example.com/x.pdf",
    "https://user:pass@arxiv.org/pdf/2312.10997",
    "https://arxiv.org:8443/pdf/2312.10997",
]
for url in blocked:
    try:
        _check_url(url)
        print("NOT BLOCKED (bad):", url)
    except DownloadError as exc:
        print("blocked:", url, "->", exc)

_check_url("https://arxiv.org/pdf/2312.10997")
print("allowed: https://arxiv.org/pdf/2312.10997")