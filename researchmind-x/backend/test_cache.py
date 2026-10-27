import time

from app.services.extraction_service import get_paper_summary

for attempt in (1, 2):
    start = time.time()
    get_paper_summary(7, user_id=2)
    print(f"call {attempt}: {time.time() - start:.1f}s")