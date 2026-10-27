from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.research import ResearchReport, ResearchRequest
from app.security import get_current_user
from app.services.workflow import run_workflow

router = APIRouter(prefix="/api/research", tags=["research"])

MAX_PAPERS = 5


@router.post("/run", response_model=ResearchReport)
def run_research(
    data: ResearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if len(data.paper_ids) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 papers")
    if len(data.paper_ids) > MAX_PAPERS:
        raise HTTPException(status_code=400, detail=f"Select at most {MAX_PAPERS} papers")
    if len(set(data.paper_ids)) != len(data.paper_ids):
        raise HTTPException(status_code=400, detail="Each paper can only be selected once")

    papers = (
        db.query(Paper)
        .filter(Paper.id.in_(data.paper_ids), Paper.user_id == user.id)
        .all()
    )
    missing = set(data.paper_ids) - {p.id for p in papers}
    if missing:
        raise HTTPException(status_code=404, detail=f"Papers not found: {sorted(missing)}")

    titles = {p.id: p.title for p in papers}
    return run_workflow(data.paper_ids, titles, user.id)