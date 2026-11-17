from pydantic import BaseModel, ConfigDict, Field

from app.schemas.search import SearchHit


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    paper_id: int | None = Field(default=None, ge=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchHit]
