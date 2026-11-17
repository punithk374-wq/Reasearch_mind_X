"""Run one research workflow and export its evidence for human gap assessment."""
import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import time

from eval_common import ApiClient, ApiError, csv_safe


def main():
    parser = argparse.ArgumentParser(description=__doc__ + " This consumes Gemini quota.")
    parser.add_argument("--paper-ids", type=int, nargs="+", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email")
    args = parser.parse_args()
    if not 2 <= len(args.paper_ids) <= 5 or len(set(args.paper_ids)) != len(args.paper_ids):
        parser.error("Choose 2 to 5 distinct ready paper IDs")
    client = ApiClient(args.base_url)
    try:
        user = client.login(args.email)
        started = time.perf_counter()
        report = client.request("/api/research/run", {"paper_ids": args.paper_ids})
        elapsed = time.perf_counter() - started
    except ApiError as exc:
        parser.exit(1, f"Workflow failed: {exc}\nNo successful evaluation result was recorded.\n")
    now = datetime.now(timezone.utc)
    output = Path("eval") / ("results_research_" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"evaluated_at": now.isoformat(), "user_id": user["id"],
                                 "total_seconds": elapsed,
                                 "cache_note": "Existing summary caches may be reused; cache state was not measured.",
                                 "report": report}, indent=2, ensure_ascii=False), encoding="utf-8")
    review = output.with_name("human_review_" + output.stem + ".csv")
    with review.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["gap_number", "title", "description", "verdict", "cited_papers", "verified_papers",
                  "evidence_support_1_to_5", "usefulness_1_to_5", "reviewer_notes"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for number, gap in enumerate(report["gaps"], 1):
            row = {"gap_number": number, "title": gap["title"], "description": gap["description"],
                   "verdict": gap["verdict"], "cited_papers": str(gap["supporting_paper_ids"]),
                   "verified_papers": str(gap["verified_paper_ids"])}
            writer.writerow({key: csv_safe(row.get(key, "")) for key in fields})
    print(f"Workflow completed in {elapsed:.2f}s; {len(report['gaps'])} retained candidate gaps.")
    print(f"Saved {output} and {review}")
    print("Assess each claim against the JSON evidence passages. No human ratings were generated.")


if __name__ == "__main__":
    main()
