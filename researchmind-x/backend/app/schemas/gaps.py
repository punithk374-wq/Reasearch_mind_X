from pydantic import BaseModel


class GapRequest(BaseModel):
    paper_ids: list[int]


class Gap(BaseModel):
    type: str
    title: str
    description: str
    supporting_paper_ids: list[int]
    evidence: str
    research_question: str


class GapPaper(BaseModel):
    paper_id: int
    title: str


class GapResponse(BaseModel):
    papers: list[GapPaper]
    gaps: list[Gap]
    note: str | None = None
    