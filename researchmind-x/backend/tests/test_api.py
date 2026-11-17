"""API integration regressions using a temporary SQLite DB and fake AI/vector services.

These tests never use the user's .env, real database, API quota, PDFs or vector store.
They check application behavior, not semantic retrieval or LLM accuracy.
"""
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pymupdf
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import event


class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        cls.directory = Path(cls.temp.name)
        config = ModuleType("app.config")
        config.settings = SimpleNamespace(
            database_url="sqlite:///" + str(cls.directory / "tests.sqlite"),
            secret_key="fixture-secret-" * 5, algorithm="HS256", access_token_expire_minutes=5,
            gemini_api_key="fixture-key-not-real", gemini_model="fixture-model",
            openalex_api_key="", semantic_scholar_api_key="",
        )
        cls.settings = config.settings
        vectors = ModuleType("app.services.vector_store")
        cls.index = {}
        def index_chunks(paper_id, user_id, chunks):
            for chunk in chunks:
                cls.index[(paper_id, chunk["id"])] = {**chunk, "chunk_id": chunk["id"],
                                                     "paper_id": paper_id, "user_id": user_id, "score": 0.8}
        def delete_vectors(paper_id):
            for key in list(cls.index):
                if key[0] == paper_id:
                    del cls.index[key]
        def search(query, user_id, top_k=5, paper_id=None):
            return [row for row in cls.index.values()
                    if row["user_id"] == user_id and (paper_id is None or row["paper_id"] == paper_id)][:top_k]
        vectors.index_chunks, vectors.delete_paper_vectors, vectors.search = index_chunks, delete_vectors, search
        cls.modules = patch.dict("sys.modules", {"app.config": config, "app.services.vector_store": vectors})
        cls.modules.start()
        cls.addClassCleanup(cls.modules.stop)
        cls.genai = patch("google.genai.Client", return_value=SimpleNamespace(
            models=SimpleNamespace(generate_content=Mock())))
        cls.genai.start()
        cls.addClassCleanup(cls.genai.stop)
        cls.main = importlib.import_module("app.main")
        cls.db_module = importlib.import_module("app.database")
        cls.security = importlib.import_module("app.security")
        cls.llm = importlib.import_module("app.services.llm_service")
        cls.papers_router = importlib.import_module("app.routers.papers")
        cls.User = importlib.import_module("app.models.user").User
        cls.Paper = importlib.import_module("app.models.paper").Paper
        cls.papers_router.UPLOAD_DIR = cls.directory / "uploads"
        @event.listens_for(cls.db_module.engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
        cls.client = TestClient(cls.main.app)
        cls.password_hash = cls.security.hash_password("fixture-password")

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.db_module.engine.dispose()
        cls.modules.stop()
        cls.temp.cleanup()

    def setUp(self):
        self.db_module.Base.metadata.drop_all(self.db_module.engine)
        self.db_module.Base.metadata.create_all(self.db_module.engine)
        self.index.clear()
        with self.db_module.SessionLocal() as db:
            for uid in (1, 2):
                db.add(self.User(id=uid, full_name=f"Fixture User {uid}", email=f"user{uid}@example.com",
                                 hashed_password=self.password_hash))
            db.commit()
        self.headers = {"Authorization": "Bearer " + self.security.create_access_token(1)}
        self.other_headers = {"Authorization": "Bearer " + self.security.create_access_token(2)}

    def upload(self):
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_textbox(pymupdf.Rect(40, 40, 550, 750), "Methods\n" +
                                "This is fixture research text for exercising PDF processing and authenticated upload. " * 8)
            pdf = doc.tobytes()
        response = self.client.post("/api/papers/upload", files={"file": ("fixture.pdf", pdf, "application/pdf")},
                                    headers=self.headers)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["status"], "ready")
        return response.json()["id"]

    def test_registration_login_wrong_password_and_duplicate(self):
        data = {"full_name": "New User", "email": "new@example.com", "password": "fixture-password"}
        self.assertEqual(self.client.post("/api/auth/register", json=data).status_code, 201)
        self.assertEqual(self.client.post("/api/auth/register", json=data).status_code, 400)
        self.assertEqual(self.client.post("/api/auth/login", data={"username": data["email"], "password": "wrong"}).status_code, 401)
        response = self.client.post("/api/auth/login", data={"username": data["email"], "password": data["password"]})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access_token", response.json())

    def test_long_unicode_password_returns_validation_error_not_500(self):
        data = {"full_name": "New User", "email": "new@example.com", "password": "ಪ" * 30}
        self.assertEqual(self.client.post("/api/auth/register", json=data).status_code, 422)
        self.assertEqual(self.client.post("/api/auth/login", data={"username": "user1@example.com", "password": "x" * 100}).status_code, 401)

    def test_bad_token_subject_returns_401(self):
        for subject in ("not-a-number", "0", "999999999999999999999"):
            token = jwt.encode({"sub": subject}, self.settings.secret_key, algorithm="HS256")
            response = self.client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
            self.assertEqual(response.status_code, 401)

    def test_upload_and_user_isolation(self):
        pid = self.upload()
        self.assertTrue(self.client.get(f"/api/papers/{pid}/chunks", headers=self.headers).json())
        self.assertEqual(self.client.get("/api/papers", headers=self.other_headers).json(), [])
        self.assertEqual(self.client.get(f"/api/papers/{pid}/chunks", headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.post("/api/search", json={"query": "methods", "paper_id": pid}, headers=self.other_headers).json(), [])

    def test_invalid_upload_is_rejected_and_partial_file_removed(self):
        before = set(self.papers_router.UPLOAD_DIR.rglob("*.pdf"))
        response = self.client.post("/api/papers/upload", files={"file": ("bad.pdf", b"not a PDF", "application/pdf")}, headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(self.papers_router.UPLOAD_DIR.rglob("*.pdf")), before)

    def test_delete_removes_document_file_chunks_and_vectors(self):
        pid = self.upload()
        with self.db_module.SessionLocal() as db:
            path = Path(db.get(self.Paper, pid).file_path)
        self.assertTrue(path.exists())
        self.assertEqual(self.client.delete(f"/api/papers/{pid}", headers=self.other_headers).status_code, 404)
        self.assertEqual(self.client.delete(f"/api/papers/{pid}", headers=self.headers).status_code, 204)
        self.assertFalse(path.exists())
        self.assertFalse(self.index)
        self.assertEqual(self.client.get(f"/api/papers/{pid}", headers=self.headers).status_code, 404)

    def test_duplicate_papers_and_failed_papers_rejected(self):
        with self.db_module.SessionLocal() as db:
            for pid, status in [(10, "ready"), (11, "failed")]:
                db.add(self.Paper(id=pid, user_id=1, title="Fixture paper", filename="fixture.pdf", file_path="unused", status=status))
            db.commit()
        for route in ("/api/compare", "/api/gaps", "/api/research/run"):
            self.assertEqual(self.client.post(route, json={"paper_ids": [10]}, headers=self.headers).status_code, 400)
            self.assertEqual(self.client.post(route, json={"paper_ids": [10, 10]}, headers=self.headers).status_code, 400)
            self.assertEqual(self.client.post(route, json={"paper_ids": [10, 11]}, headers=self.headers).status_code, 409)

    def test_invalid_citations_are_blocked(self):
        self.upload()
        with patch.object(self.llm, "_raw_generate", return_value=SimpleNamespace(text="A claim [99]")):
            response = self.client.post("/api/rag/ask", json={"question": "methods?"}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertIn("could not produce an answer with valid source citations", response.json()["answer"])

    def test_empty_library_abstains_without_a_model_call(self):
        with patch.object(self.llm, "_raw_generate") as generate:
            response = self.client.post("/api/rag/ask", json={"question": "methods?"}, headers=self.headers)
            generate.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sources"], [])

    def test_quota_message_reaches_the_client(self):
        with patch("app.routers.rag.generate_answer", side_effect=self.llm.DailyQuotaExceeded("Fixture quota exhausted")):
            response = self.client.post("/api/rag/ask", json={"question": "methods?"}, headers=self.headers)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()["detail"], "Fixture quota exhausted")

    def test_cached_summary_is_scoped_to_its_owner(self):
        pid = self.upload()
        Cache = importlib.import_module("app.models.summary").PaperSummaryCache
        service = importlib.import_module("app.services.extraction_service")
        summary = {key: "Fixture text" for key in service.ATTRIBUTE_QUERIES}
        with self.db_module.SessionLocal() as db:
            db.add(Cache(paper_id=pid, data=json.dumps(summary), model=self.settings.gemini_model))
            db.commit()
        self.assertEqual(service.get_paper_summary(pid, 1), summary)
        with self.assertRaises(ValueError):
            service.get_paper_summary(pid, 2)

    def test_comparison_handles_malformed_model_json(self):
        ids = [self.upload(), self.upload()]
        with patch.object(self.llm, "_raw_generate", return_value=SimpleNamespace(text="[]")):
            response = self.client.post("/api/compare", json={"paper_ids": ids}, headers=self.headers)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["papers"][0]["dataset"], "Not specified in available evidence")

    def test_research_graph_triages_and_handles_no_gaps(self):
        ids = [self.upload(), self.upload()]
        workflow = importlib.import_module("app.services.workflow")
        summary = {key: "Fixture evidence" for key in ("methodology", "dataset", "key_findings", "limitations", "future_work")}
        gap = {"title": "Fixture gap", "type": "recurring_limitation", "description": "Fixture description",
               "supporting_paper_ids": ids, "evidence": "Fixture evidence", "research_question": "Fixture question?"}
        verifications = [{"verdict": verdict, "supported_paper_ids": ids if verdict == "supported" else [],
                          "reason": "Fixture verdict", "passages": []} for verdict in ("supported", "unsupported")]
        evidence_text = "Supporting passage. " * 80
        verifications[0]["passages"] = [{"paper_id": ids[0], "page_number": 1, "section": None, "text": evidence_text}]
        with patch.object(workflow, "get_paper_summary", return_value=summary), \
             patch.object(workflow, "detect_gaps", return_value={"gaps": [gap, gap], "note": None}) as detect, \
             patch.object(workflow, "verify_gaps_batch", return_value=verifications) as verify:
            response = self.client.post("/api/research/run", json={"paper_ids": ids}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["gaps"]), 1)
            self.assertEqual(response.json()["dropped_count"], 1)
            self.assertEqual(response.json()["gaps"][0]["status"], "source-supported")
            self.assertEqual(response.json()["gaps"][0]["passages"][0]["text"], evidence_text)
            detect.return_value = {"gaps": [], "note": "Fixture: unrelated papers"}
            verify.reset_mock()
            empty = self.client.post("/api/research/run", json={"paper_ids": ids}, headers=self.headers)
            self.assertEqual(empty.status_code, 200, empty.text)
            self.assertEqual(empty.json()["gaps"], [])
            verify.assert_not_called()

    def test_failed_indexing_cleans_partial_vectors(self):
        with self.db_module.SessionLocal() as db:
            paper = self.Paper(user_id=1, title="placeholder", filename="unused", file_path="unused", status="ready")
            db.add(paper)
            db.commit()
        ingest = importlib.import_module("app.services.ingest_service")
        def fail_after_write(paper_id, user_id, chunks):
            self.index[(paper_id, chunks[0]["id"])] = {"paper_id": paper_id}
            raise RuntimeError("Fixture indexing failure")
        with patch.object(ingest, "index_chunks", side_effect=fail_after_write):
            with pymupdf.open() as doc:
                page = doc.new_page()
                page.insert_textbox(pymupdf.Rect(40, 40, 550, 750), "Fixture indexing input. " * 30)
                response = self.client.post("/api/papers/upload", files={"file": ("fixture.pdf", doc.tobytes(), "application/pdf")}, headers=self.headers)
        self.assertEqual(response.json()["status"], "failed")
        self.assertFalse(self.index)


if __name__ == "__main__":
    unittest.main()
