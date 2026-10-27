import re

from app.services.discovery_service import (
    DiscoveryError,
    get_openalex_work,
    search_openalex,
)
from app.services.semantic_scholar_service import (
    get_semantic_scholar_paper,
    search_semantic_scholar,
)


def _doi_key(paper: dict) -> str:
    doi = (paper.get("doi") or "").lower().strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.startswith(prefix):
            doi = doi[len(prefix):]
    return doi


def _title_key(paper: dict) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", (paper.get("title") or "").lower()).strip()
    return key if len(key) >= 10 else ""


def _dedupe(papers: list[dict]) -> list[dict]:
    kept: list[dict] = []
    index_by_key: dict[str, int] = {}

    for paper in papers:
        keys = [k for k in (_doi_key(paper), _title_key(paper)) if k]
        idx = next((index_by_key[k] for k in keys if k in index_by_key), None)

        if idx is None:
            kept.append(paper)
            idx = len(kept) - 1
        else:
            existing = kept[idx]
            if not existing["pdf_url"] and paper["pdf_url"]:
                # Prefer the copy that can actually be imported
                if not paper["abstract"] and existing["abstract"]:
                    paper = {**paper, "abstract": existing["abstract"]}
                kept[idx] = paper
            elif not existing["abstract"] and paper["abstract"]:
                existing["abstract"] = paper["abstract"]

        for k in keys:
            index_by_key[k] = idx
    return kept


def search_sources(
    source: str,
    query: str,
    per_page: int = 10,
    year_from: int | None = None,
    open_access_only: bool = False,
) -> list[dict]:
    kwargs = dict(
        per_page=per_page, year_from=year_from, open_access_only=open_access_only
    )
    if source == "openalex":
        return search_openalex(query, **kwargs)
    if source == "semanticscholar":
        return search_semantic_scholar(query, **kwargs)

    # "both": one source failing should not hide the other's results
    results: list[dict] = []
    errors: list[str] = []
    for search in (search_openalex, search_semantic_scholar):
        try:
            results.extend(search(query, **kwargs))
        except DiscoveryError as exc:
            errors.append(str(exc))
    if not results and errors:
        raise DiscoveryError(" ".join(errors))
    return _dedupe(results)


def get_paper(source: str, source_id: str) -> dict:
    if source == "semanticscholar":
        return get_semantic_scholar_paper(source_id)
    return get_openalex_work(source_id)