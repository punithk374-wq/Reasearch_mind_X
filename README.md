# ResearchMind X

ResearchMind X is a local academic research application: upload or discover PDFs,
search their text, ask questions with numbered citations, compare papers, and run
a LangGraph workflow that proposes and checks candidate research gaps.

The application lives in `researchmind-x/backend` and `researchmind-x/frontend`
relative to the Git repository root. Keep this existing directory structure.

## Stack

- Python, FastAPI, SQLAlchemy and native PostgreSQL
- PyMuPDF, Sentence-Transformers (`all-MiniLM-L6-v2`) and persistent ChromaDB
- Gemini through `google-genai`, LangGraph, OpenAlex and Semantic Scholar
- React, TypeScript, Vite and Tailwind CSS

## Existing Windows installation

Keep your working PostgreSQL database and `backend/.env`. From the repository root:

```powershell
cd researchmind-x\backend
venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
uvicorn app.main:app --reload --reload-dir app
```

In a second terminal, from the repository root:

```powershell
cd researchmind-x\frontend
npm ci
npm run build
npm run lint
npm run dev
```

Open http://localhost:5173. API documentation is at http://localhost:8000/docs.
The `.env` file and local PDF/vector/database files stay outside Git. A root
`.gitignore` also covers secrets outside the backend subdirectory.

## Fresh installation

Install Python 3.12 or 3.13, PostgreSQL, and Node.js/npm. Create a local PostgreSQL
database and a database role with a password. Docker is not required.
In `researchmind-x/backend`, create and activate a `venv`, install
`requirements-dev.txt`, copy `.env.example` to `.env`, and fill in your own database
URL, generated secret key, Gemini API key and available model name. The secret key
must have at least 32 characters. URL-encode special characters in a database
password when constructing `DATABASE_URL`. Add the discovery API keys you use.
Then start the backend and frontend with the commands above.

## Final-review validation

The automated suite uses a temporary SQLite database and fake vector/AI responses.
It checks authentication, access isolation, PDF upload/deletion, response validation,
gap verification edge cases, page boundaries and evaluation arithmetic. These are
regression checks, not measurements of Gemini accuracy, real embedding quality or
PostgreSQL performance. Live testing on the Windows installation is still required.

The evaluation workflow is in [backend/eval/README.md](researchmind-x/backend/eval/README.md).
It includes corpus export, manually labelled retrieval evaluation, optional answer
generation and a human assessment sheet for research gaps. No measured project
accuracy, latency or human scores are included in this repository.

## Evidence behavior and limits

- Generated answers must use valid numbered references or the explicit insufficient-
  evidence response. Reference validity alone does not prove factual correctness.
- A fully supported gap needs checker-reported support and retrieved passages for
  every cited paper. Malformed or inconsistent checker output is handled conservatively.
- All gaps remain candidates for human review; they are not proof of novelty.
  The checker must report coverage of all assertions, including comparisons.
  Missing coverage is unverified; unestablished assertions prevent full support.
  Source support remains model-assessed, not an independent human certification.
  Reports retain full retrieved chunks, and the UI labels stated future work
  without claiming it is unaddressed across the literature.
- New PDF uploads use chunks confined to one page and section. Existing stored chunks
  are unchanged: re-upload PDFs into a separate evaluation account to use the new
  chunker without deleting your current library. The existing `reindex` endpoint only
  rebuilds embeddings from stored chunks; it does not re-extract PDFs.
- Retrieval combines semantic candidates with BM25 keyword candidates using
  reciprocal-rank fusion. Both candidate lists are restricted to the signed-in
  user and optional selected paper before scoring. Existing chunks need no reindex.
  The lexical pass reads the scoped corpus per request; this is intended for local
  academic libraries, not yet optimized for very large collections.
- Cosine similarity is displayed as a score, not as an accuracy percentage.
  Results are ordered by hybrid relevance, so cosine scores need not descend.
- Scanned PDFs still need OCR outside this application. OCR and cloud deployment are
  optional future work, not completed features.
- API quotas and external service availability can affect live demonstrations.

The research page exports Markdown with evidence passages, notes and workflow trace.
Review the source text and wider literature before relying on a candidate gap.
