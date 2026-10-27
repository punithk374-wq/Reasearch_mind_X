from app.services.discovery_service import search_openalex

results = search_openalex(
    "retrieval augmented generation survey",
    per_page=3,
    year_from=2023,
    open_access_only=True,
)

for r in results:
    print(r["year"], "|", r["title"])
    print("   authors:", ", ".join(r["authors"][:3]), "| venue:", r["venue"])
    print("   cited by:", r["cited_by_count"], "| pdf:", r["pdf_url"])
    print("   abstract:", (r["abstract"] or "(none)")[:150], "...")
    print()