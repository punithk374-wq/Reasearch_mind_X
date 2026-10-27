from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    paper_id: int | None = None


class SearchHit(BaseModel):
    chunk_id: int
    paper_id: int
    page_number: int
    section: str | None
    text: str
    score: float