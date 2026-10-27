import requests

from app.config import settings

OPENALEX_URL = "https://api.openalex.org/works"

SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "title",
        "publication_year",
        "cited_by_count",
        "abstract_inverted_index",
        "authorships",
        "primary_location",
        "best_oa_location",
        "open_access",
    ]
)


class DiscoveryError(Exception):
    """Raised when a literature source cannot be searched."""


def _abstract_from_index(index: dict | None) -> str:
    """OpenAlex sends abstracts as {word: [positions]}; rebuild the text."""
    if not index:
        return ""
    positions: dict[int, str] = {}
    for word, spots in index.items():
        for pos in spots:
            positions[pos] = word
    return " ".join(positions[i] for i in sorted(positions))


def _pick_pdf_url(work: dict) -> str | None:
    for key in ("best_oa_location", "primary_location"):
        location = work.get(key) or {}
        if location.get("pdf_url"):
            return location["pdf_url"]
    oa_url = (work.get("open_access") or {}).get("oa_url") or ""
    if oa_url.lower().endswith(".pdf") or "/pdf/" in oa_url.lower():
        return oa_url
    return None


def _normalise(work: dict) -> dict:
    primary = work.get("primary_location") or {}
    best = work.get("best_oa_location") or {}
    source = primary.get("source") or {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in (work.get("authorships") or [])
    ]
    return {
        "source": "openalex",
        "source_id": (work.get("id") or "").rsplit("/", 1)[-1],
        "title": work.get("title") or "(untitled)",
        "authors": [a for a in authors if a][:10],
        "year": work.get("publication_year"),
        "venue": source.get("display_name"),
        "doi": work.get("doi"),
        "abstract": _abstract_from_index(work.get("abstract_inverted_index")),
        "cited_by_count": work.get("cited_by_count") or 0,
        "is_open_access": bool((work.get("open_access") or {}).get("is_oa")),
        "pdf_url": _pick_pdf_url(work),
        "landing_page_url": best.get("landing_page_url")
        or primary.get("landing_page_url"),
    }


def search_openalex(
    query: str,
    per_page: int = 10,
    year_from: int | None = None,
    open_access_only: bool = False,
) -> list[dict]:
    filters = []
    if year_from:
        filters.append(f"from_publication_date:{int(year_from)}-01-01")
    if open_access_only:
        filters.append("open_access.is_oa:true")

    params = {
        "search": query,
        "per_page": min(max(per_page, 1), 25),
        "select": SELECT_FIELDS,
    }
    if filters:
        params["filter"] = ",".join(filters)
    if settings.openalex_api_key:
        params["api_key"] = settings.openalex_api_key

    try:
        resp = requests.get(OPENALEX_URL, params=params, timeout=20)
    except requests.RequestException as exc:
        raise DiscoveryError(
            "Could not reach OpenAlex. Check your internet connection."
        ) from exc

    if resp.status_code in (401, 403):
        raise DiscoveryError(
            "OpenAlex rejected the API key. Check OPENALEX_API_KEY in .env."
        )
    if resp.status_code in (409, 429):
        raise DiscoveryError(
            "The OpenAlex daily allowance has been used up. Try again tomorrow."
        )
    if resp.status_code != 200:
        raise DiscoveryError(
            f"OpenAlex returned an unexpected error ({resp.status_code})."
        )

    return [_normalise(w) for w in resp.json().get("results", [])]
def get_openalex_work(source_id: str) -> dict:
    """Fetch one paper from OpenAlex by ID (single-record lookups are free)."""
    params = {"select": SELECT_FIELDS}
    if settings.openalex_api_key:
        params["api_key"] = settings.openalex_api_key

    try:
        resp = requests.get(f"{OPENALEX_URL}/{source_id}", params=params, timeout=20)
    except requests.RequestException as exc:
        raise DiscoveryError(
            "Could not reach OpenAlex. Check your internet connection."
        ) from exc

    if resp.status_code == 404:
        raise DiscoveryError("OpenAlex has no record of that paper.")
    if resp.status_code in (401, 403):
        raise DiscoveryError(
            "OpenAlex rejected the API key. Check OPENALEX_API_KEY in .env."
        )
    if resp.status_code in (409, 429):
        raise DiscoveryError(
            "The OpenAlex daily allowance has been used up. Try again tomorrow."
        )
    if resp.status_code != 200:
        raise DiscoveryError(
            f"OpenAlex returned an unexpected error ({resp.status_code})."
        )
    return _normalise(resp.json())