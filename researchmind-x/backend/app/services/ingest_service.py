from pathlib import Path

from sqlalchemy.orm import Session

from app.models.paper import Paper, PaperChunk
from app.services.pdf_service import process_pdf
from app.services.vector_store import index_chunks


def ingest_pdf(
    db: Session,
    user_id: int,
    saved_path: Path,
    filename: str,
    title: str | None = None,
) -> Paper:
    """Create the paper row, extract and chunk the text, and index the chunks.
    If processing fails, the paper is kept with status 'failed' and the reason."""
    paper = Paper(
        user_id=user_id,
        title=(title or Path(filename).stem)[:500],
        filename=filename[:255],
        file_path=str(saved_path),
        page_count=0,
        chunk_count=0,
        status="processing",
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    paper_id = paper.id

    try:
        result = process_pdf(str(saved_path))
        if title is None and result["title"] and len(result["title"]) > 5:
            paper.title = result["title"][:500]
        paper.page_count = result["page_count"]
        paper.chunk_count = len(result["chunks"])
        paper.status = "ready"

        chunk_rows = [
            PaperChunk(
                paper_id=paper_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                section=c.section,
                text=c.text,
            )
            for c in result["chunks"]
        ]
        db.add_all(chunk_rows)
        db.flush()  # assigns IDs to the chunk rows without committing yet

        index_chunks(
            paper_id,
            user_id,
            [
                {
                    "id": row.id,
                    "text": row.text,
                    "page_number": row.page_number,
                    "section": row.section,
                }
                for row in chunk_rows
            ],
        )
    except Exception as exc:
        db.rollback()
        paper = db.get(Paper, paper_id)
        paper.status = "failed"
        paper.error_message = str(exc)[:500]

    db.commit()
    db.refresh(paper)
    return paper