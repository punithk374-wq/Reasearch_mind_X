"""Evaluate retrieval against manual chunk labels through the authenticated API.

Keyword matches and model-generated judgments are deliberately not ground truth.
Use --with-answers only when you also want Gemini responses for human assessment.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import statistics
import time

from app.services.response_validation import CITATION_FAILURE, INSUFFICIENT_EVIDENCE, citation_audit
from eval_common import ApiClient, ApiError, collect_corpus, csv_safe


def validate_dataset(data):
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Dataset must be an object with schema_version 1")
    fingerprints = data.get("paper_fingerprints")
    if not isinstance(fingerprints, dict) or not fingerprints:
        raise ValueError("Copy paper_fingerprints from your exported corpus")
    for pid, fingerprint in fingerprints.items():
        if not str(pid).isdigit() or not isinstance(fingerprint, str) or len(fingerprint) != 64:
            raise ValueError("Invalid paper fingerprint; copy it from the corpus export")
    items = data.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Add at least one manually labelled evaluation question")
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each evaluation item must be an object")
        qid, question = item.get("id"), item.get("question")
        if not isinstance(qid, str) or not qid.strip() or qid in seen:
            raise ValueError("Every question must have a unique non-empty string id")
        seen.add(qid)
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise ValueError(f"{qid}: supply a question of 1 to 2000 characters")
        if type(item.get("answerable")) is not bool:
            raise ValueError(f"{qid}: set answerable to true or false")
        labels = item.get("relevant_chunks")
        if not isinstance(labels, list) or bool(labels) != item["answerable"]:
            raise ValueError(f"{qid}: answerable questions need chunk labels; unanswerable questions need an empty list")
        for label in labels:
            if not isinstance(label, dict) or any(type(label.get(key)) is not int or label[key] < 1
                                                 for key in ("paper_id", "chunk_id")):
                raise ValueError(f"{qid}: replace example labels with real positive paper_id and chunk_id values")
            if str(label["paper_id"]) not in fingerprints:
                raise ValueError(f"{qid}: a labelled paper is missing from paper_fingerprints")
        if len({(p["paper_id"], p["chunk_id"]) for p in labels}) != len(labels):
            raise ValueError(f"{qid}: duplicate relevance labels")
    if not any(item["answerable"] for item in items):
        raise ValueError("Include answerable questions to measure retrieval")
    return items


def score_hits(hits, relevant, ks=(1, 3, 5)):
    gold = {(p["paper_id"], p["chunk_id"]) for p in relevant}
    if not gold:
        raise ValueError("Retrieval metrics require at least one relevant chunk")
    # Repeated results must not inflate precision, recall, or reciprocal rank.
    seen, flags = set(), []
    for hit in hits[:max(ks)]:
        key = (hit["paper_id"], hit["chunk_id"])
        flags.append(int(key in gold and key not in seen))
        seen.add(key)
    scores = {}
    for k in ks:
        count = sum(flags[:k])
        scores[f"hit@{k}"] = int(count > 0)
        scores[f"precision@{k}"] = count / k
        scores[f"recall@{k}"] = count / len(gold)
    scores[f"mrr@{max(ks)}"] = next((1 / rank for rank, flag in enumerate(flags, 1) if flag), 0.0)
    return scores


def validate_corpus(dataset, papers):
    actual = {str(p["paper_id"]): p["fingerprint"] for p in papers}
    if actual != dataset["paper_fingerprints"]:
        raise ValueError("The ready-paper corpus changed. Export it again and review your relevance labels before evaluating.")
    known = {(p["paper_id"], c["id"]) for p in papers for c in p["chunks"]}
    for item in dataset["items"]:
        if any((c["paper_id"], c["chunk_id"]) not in known for c in item["relevant_chunks"]):
            raise ValueError(f"{item['id']}: a labelled chunk is missing from this user's corpus")


def run_evaluation(client, items, with_answers=False):
    rows = []
    for item in items:
        row = {"id": item["id"], "question": item["question"], "answerable": item["answerable"],
               "reference_answer": item.get("reference_answer", ""), "relevant_chunks": item["relevant_chunks"]}
        started = time.perf_counter()
        try:
            hits = client.request("/api/search", {"query": item["question"], "top_k": 5})
            if not isinstance(hits, list):
                raise ApiError("Unexpected search response")
            row["retrieval_error"] = None
        except ApiError as exc:
            hits = []
            row["retrieval_error"] = str(exc)
        row["retrieval_seconds"] = time.perf_counter() - started
        row["hits"] = hits
        if item["answerable"]:
            # Failed queries count as zero, rather than disappearing from averages.
            row["metrics"] = score_hits(hits, item["relevant_chunks"])
        if with_answers:
            started = time.perf_counter()
            try:
                reply = client.request("/api/rag/ask", {"question": item["question"], "top_k": 5})
                answer, sources = reply["answer"], reply["sources"]
                row["answer"] = answer
                row["answer_sources"] = sources
                row["citation_check"] = citation_audit(answer, len(sources))
                row["abstained"] = answer == INSUFFICIENT_EVIDENCE
                row["citation_guard_failed"] = answer == CITATION_FAILURE
                row["answer_error"] = None
            except ApiError as exc:
                row["answer_error"] = str(exc)
            row["answer_seconds"] = time.perf_counter() - started
        rows.append(row)
        print(f"{item['id']}: {'retrieval failed' if row['retrieval_error'] else 'retrieved'}")

    scored = [row["metrics"] for row in rows if "metrics" in row]
    summary = {
        "total_questions": len(rows), "answerable_questions": len(scored),
        "unanswerable_questions": len(rows) - len(scored),
        "retrieval_failures": sum(bool(row["retrieval_error"]) for row in rows),
        "retrieval_metrics": {key: statistics.mean(row[key] for row in scored) for key in scored[0]},
        "mean_retrieval_seconds": statistics.mean(row["retrieval_seconds"] for row in rows),
        "latency_note": "Client wall time, including cold-start time and errors; no warm-up excluded.",
    }
    if with_answers:
        unanswerable = [row for row in rows if not row["answerable"]]
        summary["answer_checks"] = {
            "answer_failures": sum(bool(row.get("answer_error")) for row in rows),
            "answers_with_valid_citation_indices": sum(row.get("citation_check", {}).get("valid", False) for row in rows),
            "abstentions": sum(row.get("abstained", False) for row in rows),
            "citation_guard_failures": sum(row.get("citation_guard_failed", False) for row in rows),
            "unanswerable_refusal_rate": (sum(row.get("abstained", False) for row in unanswerable) / len(unanswerable)
                                          if unanswerable else None),
            "limitation": "Valid citation indices do not measure faithfulness, answer correctness or novelty. Human assessment is required.",
        }
    return {"summary": summary, "questions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path("eval/retrieval_set.json"))
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email")
    parser.add_argument("--with-answers", action="store_true", help="Also call Gemini for every question; consumes API quota")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        dataset_bytes = args.dataset.read_bytes()
        dataset = json.loads(dataset_bytes.decode("utf-8-sig"))
        items = validate_dataset(dataset)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Dataset error: {exc}\nSee eval/README.md for annotation instructions.\n")
    client = ApiClient(args.base_url)
    try:
        user = client.login(args.email)
        validate_corpus(dataset, collect_corpus(client))
        report = run_evaluation(client, items, args.with_answers)
    except (ApiError, ValueError) as exc:
        parser.exit(1, f"Evaluation stopped: {exc}\n")
    report.update({"schema_version": 1, "evaluated_at": datetime.now(timezone.utc).isoformat(),
                   "user_id": user["id"], "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(),
                   "paper_fingerprints": dataset["paper_fingerprints"],
                   "label_method": dataset.get("annotation_status", "User-provided relevance labels; review status not recorded"),
                   "label_note": "Labels are supplied by the dataset, not independently verified by this script."})
    output = args.output or Path("eval") / ("results_retrieval_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    if output.exists():
        parser.exit(1, f"{output} already exists. Choose a new output path.\n")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print(f"Saved {output}")
    if args.with_answers:
        review = output.with_name("human_review_" + output.stem + ".csv")
        with review.open("w", encoding="utf-8-sig", newline="") as handle:
            fields = ["id", "question", "reference_answer", "answer", "faithfulness_1_to_5", "correctness_1_to_5", "reviewer_notes"]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in report["questions"]:
                writer.writerow({key: csv_safe(row.get(key, "")) for key in fields})
        print(f"Human assessment sheet: {review}; ratings are intentionally blank.")
    if report["summary"]["retrieval_failures"] or report["summary"].get("answer_checks", {}).get("answer_failures"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
