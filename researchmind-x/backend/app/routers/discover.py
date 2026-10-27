from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.discover import DiscoveredPaper, DiscoverRequest, ImportRequest
from app.schemas.paper import PaperOut
from app.security import get_current_user
from app.services.discovery_service import DiscoveryError
from app.services.download_service import DownloadError, download_pdf
from app.services.ingest_service import ingest_pdf
from app.services.sources import get_paper, search_sources

router = APIRouter(prefix="/api/discover", tags=["discover"])

UPLOAD_DIR = Path("uploads")


@router.post("/search", response_model=list[DiscoveredPaper])
def discover_search(
    data: DiscoverRequest,
    user: User = Depends(get_current_user),
):
    try:
        return search_sources(
            data.source,
            data.query.strip(),
            per_page=data.per_page,
            year_from=data.year_from,
            open_access_only=data.open_access_only,
        )
    except DiscoveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.post("/import", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def import_paper(
    data: ImportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # The server looks the paper up itself, so the PDF link always comes from
    # the source's own record and never from the browser.
    try:
        work = get_paper(data.source, data.source_id)
    except DiscoveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    if not work["pdf_url"]:
        raise HTTPException(
            status_code=400,
            detail="No open-access PDF is available for this paper. "
            "Open the publisher page instead.",
        )

    existing = (
        db.query(Paper)
        .filter(
            Paper.user_id == user.id,
            func.lower(Paper.title) == work["title"][:500].lower(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409, detail="This paper is already in your library."
        )

    try:
        saved_path = download_pdf(work["pdf_url"], UPLOAD_DIR / str(user.id))
    except DownloadError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return ingest_pdf(
        db,
        user.id,
        saved_path,
        f"{work['source']}-{work['source_id'][:12]}.pdf",
        title=work["title"],
    )