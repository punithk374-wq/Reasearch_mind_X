import unittest
from sqlalchemy import create_engine, inspect, text
from app.schema_updates import ensure_paper_domain_column


class SchemaUpdateTests(unittest.TestCase):
    def test_legacy_papers_preserved_and_update_idempotent(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE papers (id INTEGER PRIMARY KEY, title VARCHAR(500))"))
            connection.execute(text("INSERT INTO papers VALUES (1, 'Original paper')"))
        ensure_paper_domain_column(engine)
        ensure_paper_domain_column(engine)
        self.assertIn("domain", {c["name"] for c in inspect(engine).get_columns("papers")})
        with engine.connect() as connection:
            self.assertEqual(tuple(connection.execute(text("SELECT id, title, domain FROM papers")).one()), (1, "Original paper", None))
