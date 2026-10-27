from app.services.extraction_service import extract_paper_summary
from app.services.gap_service import detect_gaps
from app.services.verification_service import verify_gap

USER_ID = 2

summaries = []
for pid, title in [(7, "CoSLR"), (8, "RAG taxonomy")]:
    s = extract_paper_summary(pid, USER_ID)
    s["paper_id"] = pid
    s["title"] = title
    summaries.append(s)

gaps = detect_gaps(summaries)["gaps"]

for gap in gaps:
    v = verify_gap(gap, USER_ID)
    print(f"[{v['verdict']}] {gap['title']}")
    print("   cited:", gap["supporting_paper_ids"], "| verified:", v["supported_paper_ids"])
    print("   reason:", v["reason"])
    print()