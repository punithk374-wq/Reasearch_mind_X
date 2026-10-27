import sys
from app.services.pdf_service import process_pdf

result = process_pdf(sys.argv[1])
print("pages:", result["page_count"], "| chunks:", len(result["chunks"]))
for c in result["chunks"][:6]:
    print(f"[{c.chunk_index}] page {c.page_number} | {c.section} | {len(c.text)} chars")
    print("    ", c.text[:120])