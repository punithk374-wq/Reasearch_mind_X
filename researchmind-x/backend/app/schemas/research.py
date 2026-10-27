from pydantic import BaseModel


class ResearchRequest(BaseModel):
    paper_ids: list[int]


class Passage(BaseModel):
    paper_id: int
    page_number: int
    section: str | None = None
    text: str


class VerifiedGap(BaseModel):
    type: str
    title: str
    description: str
    supporting_paper_ids: list[int]
    evidence: str
    research_question: str
    verdict: str
    status: str
    verified_paper_ids: list[int]
    verification_reason: str
    passages: list[Passage]


class ReportPaper(BaseModel):
    paper_id: int
    title: str


class ResearchReport(BaseModel):
    papers: list[ReportPaper]
    gaps: list[VerifiedGap]
    dropped_count: int
    note: str | None = None
    trace: list[str]