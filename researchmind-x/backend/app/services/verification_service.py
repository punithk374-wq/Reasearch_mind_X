import json
import time

from google.genai import types

from app.services.llm_service import _client, MODEL
from app.services.vector_store import search as vector_search

VERIFY_SYSTEM_INSTRUCTION = """You are a strict evidence checker for a research tool. You are given
a candidate research gap and passages retrieved directly from the papers it cites. Decide
whether the passages actually back the gap. Rules:

1. A paper counts as supporting the gap ONLY if its passages explicitly state the point or
   clearly show it. A paper that merely does not mention the topic does NOT support it.
2. Judge each cited paper separately, then list the paper ids that genuinely support the gap
   in "supported_paper_ids". Use only ids from the cited list.
3. Verdict:
   - "supported": every cited paper genuinely supports the gap
   - "partial": at least one, but not all, cited papers support it
   - "unsupported": none of the cited papers support it
4. Do not use outside knowledge. Judge only from the passages given.
5. Keep "reason" to one or two plain sentences saying what the passages do or do not show.
6. Respond with ONLY a JSON object, no markdown fences, in exactly this shape:

{"verdict": "supported | partial | unsupported", "supported_paper_ids": [1], "reason": "..."}"""


def _gather_passages(gap: dict, user_id: int) -> list[dict]:
    query = f"{gap['title']}. {gap['description']}"
    passages = []
    for paper_id in gap["supporting_paper_ids"]:
        hits = vector_search(query, user_id=user_id, top_k=3, paper_id=paper_id)
        for h in hits:
            passages.append(
                {
                    "paper_id": paper_id,
                    "page_number": h["page_number"],
                    "section": h["section"],
                    "text": h["text"],
                }
            )
    return passages


def _format_prompt(gap: dict, passages: list[dict]) -> str:
    lines = []
    for p in passages:
        where = f"page {p['page_number']}"
        if p["section"]:
            where += f", {p['section']}"
        lines.append(f"[Paper {p['paper_id']}, {where}]\n{p['text']}")

    return (
        "Candidate gap:\n"
        f"Title: {gap['title']}\n"
        f"Description: {gap['description']}\n"
        f"Claimed evidence: {gap['evidence']}\n"
        f"Papers cited: {gap['supporting_paper_ids']}\n\n"
        "Passages retrieved from the cited papers:\n\n"
        + "\n\n".join(lines)
        + "\n\nReturn the JSON object now."
    )


def verify_gap(gap: dict, user_id: int) -> dict:
    passages = _gather_passages(gap, user_id)
    cited = set(gap["supporting_paper_ids"])

    if not passages:
        return {
            "verdict": "unsupported",
            "supported_paper_ids": [],
            "reason": "No passages could be retrieved from the cited papers.",
            "passages": [],
        }

    prompt = _format_prompt(gap, passages)

    last_error = None
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=VERIFY_SYSTEM_INSTRUCTION,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            verdict = data.get("verdict", "unverified")
            if verdict not in ("supported", "partial", "unsupported"):
                verdict = "unverified"
            return {
                "verdict": verdict,
                "supported_paper_ids": [
                    i for i in data.get("supported_paper_ids", []) if i in cited
                ],
                "reason": data.get("reason", ""),
                "passages": passages,
            }
        except json.JSONDecodeError:
            return {
                "verdict": "unverified",
                "supported_paper_ids": list(cited),
                "reason": "The verification response could not be read.",
                "passages": passages,
            }
        except Exception as exc:
            last_error = exc
            if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                time.sleep(2 * (attempt + 1))
                continue
            raise

    raise last_error
BATCH_SYSTEM_INSTRUCTION = """You are a strict evidence checker for a research tool. You are given
several numbered candidate research gaps. Each comes with passages retrieved directly from
the papers it cites. For EACH gap, decide whether the passages actually back it. Rules:

1. A paper counts as supporting a gap ONLY if its passages explicitly state the point or
   clearly show it. A paper that merely does not mention the topic does NOT support it.
2. List the paper ids that genuinely support the gap in "supported_paper_ids", using only
   ids from that gap's cited list.
3. Verdict:
   - "supported": every cited paper genuinely supports the gap
   - "partial": at least one, but not all, cited papers support it
   - "unsupported": none of the cited papers support it
4. Do not use outside knowledge. Judge each gap only from its own passages.
5. Keep "reason" to one or two plain sentences.
6. Respond with ONLY a JSON object, no markdown fences, with exactly one entry per gap:

{"results": [{"index": 0, "verdict": "supported | partial | unsupported",
              "supported_paper_ids": [1], "reason": "..."}]}"""


def _trim(text: str, limit: int = 900) -> str:
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


def verify_gaps_batch(gaps: list[dict], user_id: int) -> list[dict]:
    """Check every gap in ONE model call. Returns one result per gap, in order."""
    if not gaps:
        return []

    passages_per_gap = [_gather_passages(g, user_id) for g in gaps]

    blocks = []
    for i, (gap, passages) in enumerate(zip(gaps, passages_per_gap)):
        lines = []
        for p in passages:
            where = f"page {p['page_number']}"
            if p["section"]:
                where += f", {p['section']}"
            lines.append(f"[Paper {p['paper_id']}, {where}]\n{_trim(p['text'])}")
        blocks.append(
            f"=== Gap {i} ===\n"
            f"Title: {gap['title']}\n"
            f"Description: {gap['description']}\n"
            f"Claimed evidence: {gap['evidence']}\n"
            f"Papers cited: {gap['supporting_paper_ids']}\n\n"
            "Passages:\n\n" + ("\n\n".join(lines) if lines else "(none retrieved)")
        )
    prompt = "\n\n".join(blocks) + "\n\nReturn the JSON object now."

    parsed: dict[int, dict] = {}
    try:
        response = _client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=BATCH_SYSTEM_INSTRUCTION,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        data = json.loads(response.text)
        for item in data.get("results", []):
            if isinstance(item.get("index"), int):
                parsed[item["index"]] = item
    except json.JSONDecodeError:
        parsed = {}

    results = []
    for i, gap in enumerate(gaps):
        passages = passages_per_gap[i]
        cited = set(gap["supporting_paper_ids"])

        if not passages:
            results.append(
                {
                    "verdict": "unsupported",
                    "supported_paper_ids": [],
                    "reason": "No passages could be retrieved from the cited papers.",
                    "passages": [],
                }
            )
            continue

        item = parsed.get(i)
        if item is None:
            results.append(
                {
                    "verdict": "unverified",
                    "supported_paper_ids": [],
                    "reason": "The checker did not return a usable result for this gap.",
                    "passages": passages,
                }
            )
            continue

        verdict = item.get("verdict", "unverified")
        if verdict not in ("supported", "partial", "unsupported"):
            verdict = "unverified"
        results.append(
            {
                "verdict": verdict,
                "supported_paper_ids": [
                    p for p in item.get("supported_paper_ids", []) if p in cited
                ],
                "reason": item.get("reason", ""),
                "passages": passages,
            }
        )
    return results