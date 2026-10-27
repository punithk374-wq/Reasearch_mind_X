import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.paper import ChunkOut, PaperOut
from app.security import get_current_user
from app.services.ingest_service import ingest_pdf
from app.services.vector_store import delete_paper_vectors, index_chunks

router = APIRouter(prefix="/api/papers", tags=["papers"])

UPLOAD_DIR = Path("uploads")
MAX_BYTES = 20 * 1024 * 1024  # 20 MB


def get_owned_paper(db: Session, paper_id: int, user: User) -> Paper:
    paper = (
        db.query(Paper)
        .filter(Paper.id == paper_id, Paper.user_id == user.id)
        .first()
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return paper


@router.post("/upload", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def upload_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    original_name = file.filename or "paper.pdf"
    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Save under a random name; never trust the uploaded filename for the path
    user_dir = UPLOAD_DIR / str(user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    saved_path = user_dir / f"{uuid.uuid4().hex}.pdf"

    try:
        size = 0
        with open(saved_path, "wb") as out:
            while True:
                block = file.file.read(1024 * 1024)
                if not block:
                    break
                size += len(block)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="File too large (max 20 MB)")
                out.write(block)

        with open(saved_path, "rb") as check:
            if check.read(5) != b"%PDF-":
                raise HTTPException(status_code=400, detail="File is not a valid PDF")
    except HTTPException:
        saved_path.unlink(missing_ok=True)
        raise

    return ingest_pdf(db, user.id, saved_path, original_name)


@router.get("", response_model=list[PaperOut])
def list_papers(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return (
        db.query(Paper)
        .filter(Paper.user_id == user.id)
        .order_by(Paper.created_at.desc())
        .all()
    )


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return get_owned_paper(db, paper_id, user)


@router.get("/{paper_id}/chunks", response_model=list[ChunkOut])
def get_chunks(
    paper_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper = get_owned_paper(db, paper_id, user)
    return paper.chunks


@router.post("/{paper_id}/reindex", response_model=PaperOut)
def reindex_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper = get_owned_paper(db, paper_id, user)
    index_chunks(
        paper.id,
        user.id,
        [
            {
                "id": c.id,
                "text": c.text,
                "page_number": c.page_number,
                "section": c.section,
            }
            for c in paper.chunks
        ],
    )
    return paper


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    paper = get_owned_paper(db, paper_id, user)
    Path(paper.file_path).unlink(missing_ok=True)
    delete_paper_vectors(paper.id)
    db.delete(paper)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)