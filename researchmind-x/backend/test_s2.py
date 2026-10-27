from app.services.semantic_scholar_service import search_semantic_scholar

results = search_semantic_scholar(
    "retrieval augmented generation survey",
    per_page=3,
    year_from=2023,
    open_access_only=True,
)

for r in results:
    print(r["year"], "|", r["title"])
    print("   authors:", ", ".join(r["authors"][:3]), "| venue:", r["venue"])
    print("   cited by:", r["cited_by_count"], "| pdf:", r["pdf_url"])
    print("   id:", r["source_id"])
    print()