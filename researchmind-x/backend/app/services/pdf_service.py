import re
from collections import Counter
from dataclasses import dataclass

import pymupdf


@dataclass
class ChunkData:
    chunk_index: int
    page_number: int
    section: str | None
    text: str


# Canonical section names, matched against a whole heading line
CANONICAL_SECTIONS = [
    ("abstract", r"abstract"),
    ("introduction", r"introduction"),
    ("literature review", r"related work|literature (survey|review)|background"),
    ("methodology", r"methodology|methods?|proposed (system|method|approach)|materials and methods"),
        ("dataset", r"datasets?"),
    ("experiments", r"experiments?|experimental (setup|results)"),
    ("results", r"results|results and discussion|findings|evaluation"),
    ("discussion", r"discussion"),
    ("limitations", r"limitations( (and|&) future (work|scope))?"),
    ("future work", r"future (work|scope)"),
    ("conclusion", r"conclusions?( and future work)?"),
    ("references", r"references|bibliography"),
]

# Fallback: a short numbered line like "8.1 Research Input Module"
NUMBERED_HEADING = re.compile(r"^\d+(?:\.\d+)*\.?\s+([A-Z][^.!?]{2,80})$")
NUMBER_PREFIX = re.compile(r"^(?:\d+(?:\.\d+)*\.?|[IVX]+\.)\s+")

def detect_heading(line: str) -> str | None:
    if len(line) > 90:
        return None
    # Real headings start with a capital letter or a number. A lowercase start
    # is almost always a wrapped line from the middle of a sentence.
    if not (line[:1].isupper() or line[:1].isdigit()):
        return None
    text = NUMBER_PREFIX.sub("", line).strip().rstrip(":").lower()
    for name, pattern in CANONICAL_SECTIONS:
        if re.fullmatch(pattern, text):
            return name
    match = NUMBERED_HEADING.match(line)
    if match:
        return match.group(1).strip()[:100]
    return None


def extract_pages(path: str):
    """Return ([(page_number, [lines])], page_count, metadata_title)."""
    pages = []
    with pymupdf.open(path) as doc:
        page_count = len(doc)
        meta_title = (doc.metadata or {}).get("title")
        for number, page in enumerate(doc, start=1):
            text = page.get_text().replace("\x00", "")
            # Re-join words split by a hyphen at a line break
            text = re.sub(r"(\w)-\n([a-z])", r"\1\2", text)
            lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
            pages.append((number, [ln for ln in lines if ln]))
    return pages, page_count, meta_title


def _norm(line: str) -> str:
    return re.sub(r"\d", "#", line)


def remove_boilerplate(pages):
    """Drop running headers/footers and bare page numbers."""
    if len(pages) < 3:
        return pages

    counts = Counter()
    for _, lines in pages:
        counts.update({_norm(ln) for ln in lines[:2] + lines[-2:]})

    threshold = max(2, int(len(pages) * 0.6))
    boilerplate = {n for n, c in counts.items() if c >= threshold and len(n) > 3}

    cleaned = []
    for number, lines in pages:
        total = len(lines)
        kept = []
        for i, ln in enumerate(lines):
            is_edge = i < 2 or i >= total - 2
            if is_edge and (_norm(ln) in boilerplate or re.fullmatch(r"\d{1,4}", ln)):
                continue
            kept.append(ln)
        cleaned.append((number, kept))
    return cleaned


def _find_cut(text: str, limit: int) -> int:
    """Best place to cut a chunk: sentence end, else a space, else the limit."""
    window = text[:limit]
    idx = max(window.rfind(". "), window.rfind("? "), window.rfind("! "))
    if idx > limit * 0.5:
        return idx + 1
    idx = window.rfind(" ")
    return idx if idx > limit * 0.5 else limit


def build_chunks(pages, max_chars: int = 1000, overlap: int = 150):
    """Section-aware chunking: a chunk never crosses a section heading."""
    chunks: list[ChunkData] = []
    section: str | None = None
    buffer = ""
    buffer_page = 1
    has_new = False

    def emit(text: str, page: int, sec: str | None):
        text = text.strip()
        if len(text) >= 40:
            chunks.append(ChunkData(len(chunks), page, sec, text))

    for page_number, lines in pages:
        for line in lines:
            heading = detect_heading(line)
            if heading:
                if has_new:
                    emit(buffer, buffer_page, section)
                buffer, has_new = "", False
                section = heading
                continue

            if not buffer:
                buffer_page = page_number
            buffer = f"{buffer} {line}".strip()
            has_new = True

            while len(buffer) > max_chars:
                cut = _find_cut(buffer, max_chars)
                emit(buffer[:cut], buffer_page, section)
                has_new = bool(buffer[cut:].strip())
                buffer = buffer[cut - overlap:].strip()
                buffer_page = page_number

    if has_new:
        emit(buffer, buffer_page, section)
    return chunks


def process_pdf(path: str) -> dict:
    pages, page_count, meta_title = extract_pages(path)

    total_chars = sum(len(ln) for _, lines in pages for ln in lines)
    if total_chars < 200:
        raise ValueError("No extractable text found. The PDF may be scanned images.")

    pages = remove_boilerplate(pages)
    chunks = build_chunks(pages)
    return {
        "page_count": page_count,
        "title": (meta_title or "").strip() or None,
        "chunks": chunks,
    }