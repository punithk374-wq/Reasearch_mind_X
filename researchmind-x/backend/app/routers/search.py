from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.search import SearchHit, SearchRequest
from app.security import get_current_user
from app.services.vector_store import search as vector_search

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=list[SearchHit])
def search_papers(
    data: SearchRequest,
    user: User = Depends(get_current_user),
):
    return vector_search(
        data.query,
        user_id=user.id,
        top_k=data.top_k,
        paper_id=data.paper_id,
    )