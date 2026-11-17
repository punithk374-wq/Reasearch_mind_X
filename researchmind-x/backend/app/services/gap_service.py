import json
import time

from google.genai import types

from app.services.llm_service import _client, MODEL

GAP_SYSTEM_INSTRUCTION = """You are a research analyst helping a researcher identify CANDIDATE
research gaps across a small set of academic papers. You are given a structured summary of
each paper. Work ONLY from these summaries. Rules:

1. Look for four kinds of patterns across the papers:
   - "recurring_limitation": the same weakness appears in two or more papers
   - "underrepresented_approach": a method, dataset, population or setting is missing or
     rarely covered across the papers
   - "inconsistent_findings": papers report conflicting or hard-to-reconcile results
   - "unaddressed_future_work": a paper's explicitly stated future research direction;
     this category does NOT establish that other papers leave it unaddressed
2. Every gap MUST list the paper_ids that support it, in "supporting_paper_ids", and a
   short "evidence" string quoting or closely paraphrasing what those papers say.
3. Do NOT invent facts. If the summaries do not support a gap, do not include it. It is
   better to return fewer gaps than to speculate. If the papers are too unrelated to
   compare meaningfully, return an empty gaps list and explain in "note".
4. These are CANDIDATE gaps for human review. Never claim a gap is proven or novel.
   Missing information in a summary is not evidence of absence in a paper. Do not
   say other papers fail to address a topic based on summary omissions. Attribute
   future-work claims to the source paper without adding unsupported comparisons.
5. For each gap, propose one concrete "research_question" a researcher could investigate.
6. Respond with ONLY a JSON object, no markdown fences, in exactly this shape:

{
  "gaps": [
    {
      "type": "recurring_limitation | underrepresented_approach | inconsistent_findings | unaddressed_future_work",
      "title": "short label",
      "description": "one or two sentences explaining the gap",
      "supporting_paper_ids": [1, 2],
      "evidence": "what the papers say that supports this",
      "research_question": "one concrete question"
    }
  ],
  "note": "optional caveat, for example if the papers are too unrelated"
}"""


def _format_summaries(summaries: list[dict]) -> str:
    blocks = []
    for s in summaries:
        blocks.append(
            f"Paper {s['paper_id']}: {s['title']}\n"
            f"- Methodology: {s['methodology']}\n"
            f"- Dataset: {s['dataset']}\n"
            f"- Key findings: {s['key_findings']}\n"
            f"- Limitations: {s['limitations']}\n"
            f"- Future work: {s['future_work']}"
        )
    return "\n\n".join(blocks)


def detect_gaps(summaries: list[dict]) -> dict:
    prompt = (
        "Paper summaries:\n\n"
        f"{_format_summaries(summaries)}\n\n"
        "Return the JSON object now."
    )

    last_error = None
    for attempt in range(3):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=GAP_SYSTEM_INSTRUCTION,
                    temperature=0.2,
                    response_mime_type="application/json",
                ),
            )
            data = json.loads(response.text)
            return _clean(data, {s["paper_id"] for s in summaries})
        except (json.JSONDecodeError, TypeError):
            return {"gaps": [], "note": "The model returned an unreadable response. Please try again."}
        except Exception as exc:
            last_error = exc
            if "503" in str(exc) or "UNAVAILABLE" in str(exc):
                time.sleep(2 * (attempt + 1))
                continue
            raise

    raise last_error


def _clean(data: dict, valid_ids: set[int]) -> dict:
    """Drop malformed gaps and any cited paper id that was not in the request."""
    if not isinstance(data, dict) or not isinstance(data.get("gaps"), list):
        return {"gaps": [], "note": "The model returned an invalid gap response. Please try again."}
    cleaned = []
    allowed_types = {"recurring_limitation", "underrepresented_approach",
                     "inconsistent_findings", "unaddressed_future_work"}
    for gap in data.get("gaps", []):
        if not isinstance(gap, dict) or not isinstance(gap.get("type"), str) or gap["type"] not in allowed_types:
            continue
        source_ids = gap.get("supporting_paper_ids")
        if not isinstance(source_ids, list):
            continue
        ids = sorted({i for i in source_ids if type(i) is int and i in valid_ids})
        fields = ("title", "description", "evidence", "research_question")
        if not ids or any(not isinstance(gap.get(key), str) or not gap[key].strip() for key in fields):
            continue
        cleaned.append(
            {
                "type": gap.get("type", "recurring_limitation"),
                "title": gap["title"],
                "description": gap["description"],
                "supporting_paper_ids": ids,
                "evidence": gap.get("evidence", ""),
                "research_question": gap.get("research_question", ""),
            }
        )
    note = data.get("note")
    return {"gaps": cleaned, "note": note if isinstance(note, str) else None}
