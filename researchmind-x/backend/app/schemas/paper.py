from datetime import datetime
from pydantic import BaseModel


class PaperOut(BaseModel):
    id: int
    title: str
    filename: str
    page_count: int
    chunk_count: int
    status: str
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChunkOut(BaseModel):
    id: int
    chunk_index: int
    page_number: int
    section: str | None = None
    text: str

    model_config = {"from_attributes": True}