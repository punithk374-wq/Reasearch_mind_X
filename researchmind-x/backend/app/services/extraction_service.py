import json
import time
from app.database import SessionLocal
from app.models.summary import PaperSummaryCache

from google.genai import types

from app.services.llm_service import _client, MODEL
from app.services.vector_store import search as vector_search

# Each attribute gets its own targeted retrieval query within the paper
ATTRIBUTE_QUERIES = {
    "methodology": "methodology, approach, proposed method, system design",
    "dataset": "dataset, data used, benchmark, corpus",
    "key_findings": "results, findings, evaluation, key contributions",
    "limitations": "limitations, weaknesses, threats to validity, constraints",
    "future_work": "future work, future scope, next steps",
}

EXTRACTION_SYSTEM_INSTRUCTION = """You are a research paper analyst. You will be given labeled
evidence passages from ONE academic paper, grouped by topic. Extract a structured summary
using ONLY the evidence provided. Respond with ONLY a JSON object, no markdown fences, no
extra text, in exactly this shape:

{
  "methodology": "one or two sentences, or 'Not specified in available evidence' if absent",
  "dataset": "one or two sentences, or 'Not specified in available evidence' if absent",
  "key_findings": "one or two sentences, or 'Not specified in available evidence' if absent",
  "limitations": "one or two sentences, or 'Not specified in available evidence' if absent",
  "future_work": "one or two sentences, or 'Not specified in available evidence' if absent"
}

Do not invent information. If the evidence for a field is weak or missing, say so plainly
in that field rather than guessing."""


def _gather_evidence(paper_id: int, user_id: int) -> str:
    sections = []
    for attribute, query in ATTRIBUTE_QUERIES.items():
        hits = vector_search(query, user_id=user_id, top_k=3, paper_id=paper_id)
        if not hits:
            continue
        label = attribute.replace("_", " ").title()
        passages = "\n".join(f"- {h['text']}" for h in hits)
        sections.append(f"### {label}\n{passages}")
    return "\n\n".join(sections)


def extract_paper_summary(paper_id: int, user_id: int) -> dict:
    evidence = _gather_evidence(paper_id, user_id)
    if not evidence:
        return {
            "methodology": "Not specified in available evidence",
            "dataset": "Not specified in available evidence",
            "key_findings": "Not specified in available evidence",
            "limitations": "Not specified in available evidence",
            "future_work": "Not specified in available evidence",
        }

    prompt = f"Evidence grouped by topic:\n\n{evidence}\n\nReturn the JSON object now."

    last_error = None
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
            return json.loads(response.text)
        except json.JSONDecodeError:
            return {
                "methodology": "Could not parse extraction",
                "dataset": "Could not parse extraction",
                "key_findings": "Could not parse extraction",
                "limitations": "Could not parse extraction",
                "future_work": "Could not parse extraction",
            }
        except Exception as exc:
            last_error = exc
            if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                time.sleep(2 * (attempt + 1))  # wait a bit longer each retry
                continue
            raise

    raise last_error
def _is_cacheable(summary: dict) -> bool:
    """Don't store failed or empty extractions, so they get retried next time."""
    values = [str(v) for v in summary.values()]
    return not all(
        v.startswith("Not specified") or v.startswith("Could not parse")
        for v in values
    )


def get_paper_summary(paper_id: int, user_id: int, force: bool = False) -> dict:
    """Return the stored summary if there is one, otherwise extract and store it."""
    db = SessionLocal()
    try:
        row = db.query(PaperSummaryCache).filter_by(paper_id=paper_id).first()
        if row and not force:
            return json.loads(row.data)

        summary = extract_paper_summary(paper_id, user_id)

        if _is_cacheable(summary):
            if row:
                row.data = json.dumps(summary)
                row.model = MODEL
            else:
                db.add(
                    PaperSummaryCache(
                        paper_id=paper_id, data=json.dumps(summary), model=MODEL
                    )
                )
            db.commit()
        return summary
    finally:
        db.close()