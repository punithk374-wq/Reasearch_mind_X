from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.comparison import CompareRequest, CompareResponse, PaperSummary
from app.security import get_current_user
from app.services.extraction_service import get_paper_summary

router = APIRouter(prefix="/api/compare", tags=["comparison"])

MAX_PAPERS = 5


@router.post("", response_model=CompareResponse)
def compare_papers(
    data: CompareRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(data.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 papers to compare")
    if len(data.paper_ids) > MAX_PAPERS:
        raise HTTPException(status_code=400, detail=f"Compare at most {MAX_PAPERS} papers at once")

    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(data.paper_ids), Paper.user_id == user.id)
        .all()
    )
    found_ids = {p.id for p in papers}
    missing = set(data.paper_ids) - found_ids
    if missing:
        raise HTTPException(status_code=404, detail=f"Papers not found: {sorted(missing)}")

    # Keep the order the user requested, not the order the DB returned
    by_id = {p.id: p for p in papers}
    ordered = [by_id[pid] for pid in data.paper_ids]

    summaries = []
    for paper in ordered:
        extraction = get_paper_summary(paper.id, user.id)
        summaries.append(
            PaperSummary(
                paper_id=paper.id,
                title=paper.title,
                methodology=extraction["methodology"],
                dataset=extraction["dataset"],
                key_findings=extraction["key_findings"],
                limitations=extraction["limitations"],
                future_work=extraction["future_work"],
            )
        )

    return CompareResponse(papers=summaries)