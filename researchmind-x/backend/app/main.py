from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app import models  # noqa: F401  (registers the tables)
from app.routers import (
    auth,
    comparison,
    discover,
    gaps,
    papers,
    rag,
    research,
    search,
)
from app.services.llm_service import DailyQuotaExceeded

# Creates tables if they don't exist yet. We'll switch to Alembic migrations later.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ResearchMind X API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DailyQuotaExceeded)
async def quota_exceeded_handler(request: Request, exc: DailyQuotaExceeded):
    return JSONResponse(status_code=429, content={"detail": str(exc)})


app.include_router(auth.router)
app.include_router(papers.router)
app.include_router(search.router)
app.include_router(rag.router)
app.include_router(comparison.router)
app.include_router(gaps.router)
app.include_router(research.router)
app.include_router(discover.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ResearchMind X"}