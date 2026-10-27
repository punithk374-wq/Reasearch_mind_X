from pydantic import BaseModel

from app.schemas.search import SearchHit


class AskRequest(BaseModel):
    question: str
    top_k: int = 5
    paper_id: int | None = None


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]