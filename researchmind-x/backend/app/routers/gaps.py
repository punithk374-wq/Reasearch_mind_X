from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.gaps import GapPaper, GapRequest, GapResponse
from app.security import get_current_user
from app.services.extraction_service import get_paper_summary
from app.services.gap_service import detect_gaps

router = APIRouter(prefix="/api/gaps", tags=["gaps"])

MAX_PAPERS = 5


@router.post("", response_model=GapResponse)
def find_gaps(
    data: GapRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(data.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 papers to analyse")
    if len(data.paper_ids) > MAX_PAPERS:
        raise HTTPException(status_code=400, detail=f"Analyse at most {MAX_PAPERS} papers at once")

    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(data.paper_ids), Paper.user_id == user.id)
        .all()
    )
    missing = set(data.paper_ids) - {p.id for p in papers}
    if missing:
        raise HTTPException(status_code=404, detail=f"Papers not found: {sorted(missing)}")

    by_id = {p.id: p for p in papers}
    ordered = [by_id[pid] for pid in data.paper_ids]

    summaries = []
    for paper in ordered:
        extraction = get_paper_summary(paper.id, user.id)
        extraction["paper_id"] = paper.id
        extraction["title"] = paper.title
        summaries.append(extraction)

    result = detect_gaps(summaries)

    return GapResponse(
        papers=[GapPaper(paper_id=p.id, title=p.title) for p in ordered],
        gaps=result["gaps"],
        note=result.get("note") or None,
    )