"""Export the signed-in user's ready papers for manual relevance annotation."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from eval_common import ApiClient, ApiError, collect_corpus


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email")
    parser.add_argument("--output", type=Path, default=Path("eval/corpus.json"))
    args = parser.parse_args()
    client = ApiClient(args.base_url)
    try:
        user = client.login(args.email)
        papers = collect_corpus(client)
    except ApiError as exc:
        parser.exit(1, f"{exc}\n")
    if not papers:
        parser.exit(1, "No ready papers found. Upload and process your evaluation papers first.\n")
    if args.output.exists():
        parser.exit(1, f"{args.output} already exists. Choose a new --output path to preserve it.\n")
    payload = {"schema_version": 1, "exported_at": datetime.now(timezone.utc).isoformat(),
               "user_id": user["id"], "papers": papers,
               "paper_fingerprints": {str(p["paper_id"]): p["fingerprint"] for p in papers}}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Exported {len(papers)} ready papers to {args.output}.")
    print("This file contains paper text and IDs, but no password, token or API key.")
    print("Label relevant chunks manually before running eval_retrieval.py. No AI calls were made.")


if __name__ == "__main__":
    main()
