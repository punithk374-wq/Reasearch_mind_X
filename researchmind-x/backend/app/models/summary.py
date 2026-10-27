from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.database import Base


class PaperSummaryCache(Base):
    __tablename__ = "paper_summaries"

    id = Column(Integer, primary_key=True)
    paper_id = Column(
        Integer,
        ForeignKey("papers.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    data = Column(Text, nullable=False)  # the extraction, stored as JSON text
    model = Column(String(100), nullable=False)  # which model produced it
    created_at = Column(DateTime(timezone=True), server_default=func.now())