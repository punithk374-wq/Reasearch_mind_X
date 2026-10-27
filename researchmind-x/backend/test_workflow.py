from app.services.workflow import run_workflow

report = run_workflow([7, 8], {7: "CoSLR", 8: "RAG taxonomy"}, user_id=2)

print("TRACE")
for line in report["trace"]:
    print("  ", line)

print()
for g in report["gaps"]:
    print(f"[{g['status']}] {g['title']}")
    print("   claimed:", g["supporting_paper_ids"], "| verified:", g["verified_paper_ids"])
    print("   reason:", g["verification_reason"])
print()
print("dropped as unsupported:", report["dropped_count"])