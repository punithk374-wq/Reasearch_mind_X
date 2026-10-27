from pydantic import BaseModel


class CompareRequest(BaseModel):
    paper_ids: list[int]


class PaperSummary(BaseModel):
    paper_id: int
    title: str
    methodology: str
    dataset: str
    key_findings: str
    limitations: str
    future_work: str


class CompareResponse(BaseModel):
    papers: list[PaperSummary]