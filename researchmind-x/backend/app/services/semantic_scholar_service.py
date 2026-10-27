import requests

from app.config import settings
from app.services.discovery_service import DiscoveryError

S2_BASE = "https://api.semanticscholar.org/graph/v1"

FIELDS = ",".join(
    [
        "paperId",
        "title",
        "abstract",
        "year",
        "venue",
        "citationCount",
        "authors",
        "openAccessPdf",
        "externalIds",
        "url",
        "isOpenAccess",
    ]
)


def _headers() -> dict:
    headers = {"User-Agent": "ResearchMindX/1.0 (academic project)"}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key
    return headers


def _normalise(p: dict) -> dict:
    doi = (p.get("externalIds") or {}).get("DOI")
    oa = p.get("openAccessPdf") or {}
    return {
        "source": "semanticscholar",
        "source_id": p.get("paperId") or "",
        "title": p.get("title") or "(untitled)",
        "authors": [
            a["name"] for a in (p.get("authors") or []) if a.get("name")
        ][:10],
        "year": p.get("year"),
        "venue": p.get("venue") or None,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "abstract": p.get("abstract") or "",
        "cited_by_count": p.get("citationCount") or 0,
        "is_open_access": bool(oa.get("url")) or bool(p.get("isOpenAccess")),
        "pdf_url": oa.get("url") or None,
        "landing_page_url": p.get("url"),
    }


def _check(resp: requests.Response) -> None:
    if resp.status_code == 429:
        raise DiscoveryError(
            "Semantic Scholar is busy right now (its free tier is shared). "
            "Wait a few seconds and try again, or add a free API key."
        )
    if resp.status_code in (401, 403):
        raise DiscoveryError(
            "Semantic Scholar rejected the API key. "
            "Check SEMANTIC_SCHOLAR_API_KEY in .env."
        )
    if resp.status_code == 404:
        raise DiscoveryError("Semantic Scholar has no record of that paper.")
    if resp.status_code != 200:
        raise DiscoveryError(
            f"Semantic Scholar returned an unexpected error ({resp.status_code})."
        )


def search_semantic_scholar(
    query: str,
    per_page: int = 10,
    year_from: int | None = None,
    open_access_only: bool = False,
) -> list[dict]:
    # When filtering to open access we filter here instead of relying on a
    # server-side flag, so ask for extra results to still fill the page.
    limit = 40 if open_access_only else min(max(per_page, 1), 25)
    params = {"query": query, "limit": limit, "fields": FIELDS}
    if year_from:
        params["year"] = f"{int(year_from)}-"  # "2022-" means 2022 and later

    try:
        resp = requests.get(
            f"{S2_BASE}/paper/search", params=params, headers=_headers(), timeout=20
        )
    except requests.RequestException as exc:
        raise DiscoveryError(
            "Could not reach Semantic Scholar. Check your internet connection."
        ) from exc
    _check(resp)

    papers = [_normalise(p) for p in resp.json().get("data", [])]
    if open_access_only:
        papers = [p for p in papers if p["pdf_url"]]
    return papers[:per_page]


def get_semantic_scholar_paper(paper_id: str) -> dict:
    try:
        resp = requests.get(
            f"{S2_BASE}/paper/{paper_id}",
            params={"fields": FIELDS},
            headers=_headers(),
            timeout=20,
        )
    except requests.RequestException as exc:
        raise DiscoveryError(
            "Could not reach Semantic Scholar. Check your internet connection."
        ) from exc
    _check(resp)
    return _normalise(resp.json())