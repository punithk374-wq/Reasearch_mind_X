import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DiscoverRequest(BaseModel):
    query: str = Field(min_length=3, max_length=300)
    per_page: int = Field(default=10, ge=1, le=25)
    year_from: int | None = Field(default=None, ge=1900, le=2100)
    open_access_only: bool = False
    source: Literal["openalex", "semanticscholar", "both"] = "openalex"


class DiscoveredPaper(BaseModel):
    source: str
    source_id: str
    title: str
    authors: list[str]
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    abstract: str
    cited_by_count: int
    is_open_access: bool
    pdf_url: str | None = None
    landing_page_url: str | None = None


class ImportRequest(BaseModel):
    source: Literal["openalex", "semanticscholar"] = "openalex"
    source_id: str

    @model_validator(mode="after")
    def id_matches_source(self):
        pattern = r"W\d{3,15}" if self.source == "openalex" else r"[0-9a-f]{40}"
        if not re.fullmatch(pattern, self.source_id):
            raise ValueError("source_id is not a valid id for this source")
        return self