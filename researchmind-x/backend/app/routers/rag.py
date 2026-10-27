from fastapi import APIRouter, Depends

from app.models.user import User
from app.schemas.rag import AskRequest, AskResponse
from app.security import get_current_user
from app.services.llm_service import generate_answer
from app.services.vector_store import search as vector_search

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/ask", response_model=AskResponse)
def ask(
    data: AskRequest,
    user: User = Depends(get_current_user),
):
    hits = vector_search(
        data.question,
        user_id=user.id,
        top_k=data.top_k,
        paper_id=data.paper_id,
    )

    # Number the hits 1, 2, 3... so the LLM's citations map back to `hits`
    context_chunks = [
        {
            "index": i + 1,
            "text": h["text"],
            "paper_id": h["paper_id"],
            "page_number": h["page_number"],
            "section": h["section"],
        }
        for i, h in enumerate(hits)
    ]

    answer = generate_answer(data.question, context_chunks)

    return AskResponse(answer=answer, sources=hits)