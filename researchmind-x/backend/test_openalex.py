import requests

from app.config import settings

params = {
    "search": "retrieval augmented generation survey",
    "per_page": 3,
    "select": "id,title,publication_year,doi,cited_by_count,open_access",
}
if settings.openalex_api_key:
    params["api_key"] = settings.openalex_api_key

resp = requests.get("https://api.openalex.org/works", params=params, timeout=20)
print("status:", resp.status_code)

for w in resp.json().get("results", []):
    oa = w.get("open_access") or {}
    print(w["publication_year"], "| cited by", w["cited_by_count"], "|", w["title"])
    print("   open access:", oa.get("is_oa"), "|", oa.get("oa_url"))