"""Structural checks for model output; these do not establish factual correctness."""
import re

INSUFFICIENT_EVIDENCE = "The selected papers do not contain enough information to answer this question."
CITATION_FAILURE = "I could not produce an answer with valid source citations. Please review the retrieved passages or try a more specific question."
SUMMARY_FIELDS = ("methodology", "dataset", "key_findings", "limitations", "future_work")
MISSING_FIELD = "Not specified in available evidence"


def citation_audit(answer: str, source_count: int) -> dict:
    """Check numbered references, not whether the sources entail the claims."""
    markers = re.findall(r"\[([^\[\]\n]+)\]", answer)
    numeric = [m for m in markers if re.fullmatch(r"[\d\s,;\-–]+", m)]
    numbers, malformed = [], []
    for marker in numeric:
        if not re.fullmatch(r"[0-9]{1,9}", marker):
            malformed.append(marker)
        else:
            numbers.append(int(marker))
    invalid = sorted({n for n in numbers if not 1 <= n <= source_count})
    return {"citations": sorted(set(numbers)), "invalid_citations": invalid,
            "malformed_citations": malformed,
            "valid": bool(numbers) and not invalid and not malformed}


def validate_grounded_answer(answer: object, source_count: int) -> str:
    if not isinstance(answer, str) or not answer.strip():
        return CITATION_FAILURE
    answer = answer.strip()
    if answer == INSUFFICIENT_EVIDENCE:
        return answer
    return answer if citation_audit(answer, source_count)["valid"] else CITATION_FAILURE


def normalise_summary(data: object) -> dict:
    if not isinstance(data, dict):
        data = {}
    return {key: value.strip() if isinstance(value := data.get(key), str) and value.strip()
            else MISSING_FIELD for key in SUMMARY_FIELDS}
