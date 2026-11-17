from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    paper_id: int | None = Field(default=None, ge=1)


class SearchHit(BaseModel):
    chunk_id: int
    paper_id: int
    page_number: int
    section: str | None
    text: str
    score: float
