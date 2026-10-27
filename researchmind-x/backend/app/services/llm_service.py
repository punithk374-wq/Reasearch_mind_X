import time
from google import genai
from google.genai import types

from app.config import settings

_client = genai.Client(api_key=settings.gemini_api_key)
_raw_generate = _client.models.generate_content


class DailyQuotaExceeded(Exception):
    """The free-tier daily request limit for the model has been used up."""


def _generate_with_retry(*args, **kwargs):
    """Retry on per-minute limits (429) and temporary overload (503).
    A daily limit cannot be waited out, so it fails immediately."""
    last_error = None
    for attempt in range(4):
        try:
            return _raw_generate(*args, **kwargs)
        except Exception as exc:
            message = str(exc)
            if "PerDay" in message:
                raise DailyQuotaExceeded(
                    "The daily free-tier limit for the AI model has been reached. "
                    "It resets every day at midnight Pacific time. Try again later, "
                    "or switch to a different model."
                ) from exc
            if "429" in message or "RESOURCE_EXHAUSTED" in message:
                wait = 20 + 10 * attempt
            elif "503" in message or "UNAVAILABLE" in message:
                wait = 2 * (attempt + 1)
            else:
                raise
            last_error = exc
            time.sleep(wait)
    raise last_error


_client.models.generate_content = _generate_with_retry

MODEL = settings.gemini_model

SYSTEM_INSTRUCTION = """You are ResearchMind X, a research assistant that answers questions
using ONLY the evidence passages provided to you. Follow these rules strictly:

1. Base your answer only on the provided evidence. Do not use outside knowledge.
2. Every factual claim in your answer must be supported by at least one evidence passage.
3. Cite evidence using the bracketed number next to each passage, like [1] or [2][3].
4. If the evidence does not contain enough information to answer the question,
   say so plainly instead of guessing or inventing an answer.
5. Keep your answer concise and directly focused on the question.
6. Do not refer to "the evidence" or "the passages" in your answer; write as if you
   are directly informed by the papers, and just use the citation numbers."""


def build_context(chunks: list[dict]) -> str:
    """chunks: list of {index, text, paper_id, page_number, section}"""
    parts = []
    for c in chunks:
        label = f"[{c['index']}] (paper {c['paper_id']}, page {c['page_number']}"
        if c["section"]:
            label += f", {c['section']}"
        label += ")"
        parts.append(f"{label}\n{c['text']}")
    return "\n\n".join(parts)


def generate_answer(question: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I couldn't find any relevant evidence in your papers to answer this question."

    context = build_context(chunks)
    prompt = f"Evidence:\n\n{context}\n\nQuestion: {question}\n\nAnswer:"

    response = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
        ),
    )
    return response.text or "No answer was generated."