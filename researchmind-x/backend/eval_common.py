"""Small authenticated API client used by the local evaluation tools."""
import getpass
import hashlib
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener


class ApiError(RuntimeError):
    pass


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class ApiClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self.token = None
        self.opener = build_opener(NoRedirects())

    def request(self, path, data=None, form=False):
        headers = {"Accept": "application/json"}
        body = None
        if data is not None:
            headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
            body = (urlencode(data) if form else json.dumps(data)).encode("utf-8")
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            with self.opener.open(Request(self.base_url + path, data=body, headers=headers), timeout=180) as response:
                return json.load(response)
        except HTTPError as exc:
            try:
                detail = json.load(exc).get("detail", "Request failed")
            except (ValueError, AttributeError):
                detail = "Request failed"
            raise ApiError(f"HTTP {exc.code}: {detail}") from None
        except (URLError, TimeoutError) as exc:
            raise ApiError("Could not reach the backend. Check that Uvicorn is running.") from exc

    def login(self, email=None):
        email = email or input("ResearchMind X login email: ").strip()
        password = getpass.getpass("ResearchMind X login password (hidden): ")
        response = self.request("/api/auth/login", {"username": email, "password": password}, form=True)
        self.token = response["access_token"]
        return self.request("/api/auth/me")


def chunk_fingerprint(chunks):
    canonical = [{key: chunk.get(key) for key in ("id", "page_number", "section", "text")}
                 for chunk in sorted(chunks, key=lambda chunk: chunk["id"])]
    encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def csv_safe(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def collect_corpus(client):
    papers = []
    for paper in client.request("/api/papers"):
        if paper["status"] != "ready":
            continue
        chunks = client.request(f"/api/papers/{paper['id']}/chunks")
        papers.append({"paper_id": paper["id"], "title": paper["title"],
                       "filename": paper["filename"], "page_count": paper["page_count"],
                       "fingerprint": chunk_fingerprint(chunks), "chunks": chunks})
    return sorted(papers, key=lambda paper: paper["paper_id"])
