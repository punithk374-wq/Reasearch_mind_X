import unittest

from pydantic import ValidationError

from app.schemas.rag import AskRequest
from app.schemas.search import SearchRequest
from app.schemas.user import UserCreate
from app.services.response_validation import (
    CITATION_FAILURE, INSUFFICIENT_EVIDENCE, MISSING_FIELD,
    citation_audit, normalise_summary, validate_grounded_answer,
)


class ResponseTests(unittest.TestCase):
    def test_valid_citations_are_retained(self):
        self.assertEqual(validate_grounded_answer("A supported claim [1][2].", 2), "A supported claim [1][2].")

    def test_bad_or_missing_citations_are_not_presented_as_answers(self):
        for answer in ["Uncited claim", "A claim [0]", "A claim [3]", "A claim [1][1-3]", None, ""]:
            with self.subTest(answer=answer):
                self.assertEqual(validate_grounded_answer(answer, 2), CITATION_FAILURE)

    def test_exact_abstention_is_allowed(self):
        self.assertEqual(validate_grounded_answer(INSUFFICIENT_EVIDENCE, 2), INSUFFICIENT_EVIDENCE)

    def test_reference_check_does_not_claim_faithfulness(self):
        self.assertTrue(citation_audit("A potentially false claim [1].", 1)["valid"])

    def test_malformed_summaries_have_all_required_fields(self):
        summary = normalise_summary({"methodology": " A method ", "dataset": ["invalid"]})
        self.assertEqual(summary["methodology"], "A method")
        self.assertEqual(summary["dataset"], MISSING_FIELD)
        self.assertEqual(len(normalise_summary(None)), 5)

    def test_whitespace_queries_and_unbounded_top_k_are_rejected(self):
        for cls, field in [(SearchRequest, "query"), (AskRequest, "question")]:
            for data in [{field: "   "}, {field: "question", "top_k": 0},
                         {field: "question", "top_k": 21}, {field: "question", "paper_id": -1}]:
                with self.subTest(cls=cls.__name__, data=data):
                    with self.assertRaises(ValidationError):
                        cls(**data)

    def test_password_limit_counts_utf8_bytes(self):
        with self.assertRaises(ValidationError):
            UserCreate(full_name="Test User", email="user@example.com", password="ಪ" * 30)
        user = UserCreate(full_name=" Test User ", email="user@example.com", password="a" * 72)
        self.assertEqual(user.full_name, "Test User")


if __name__ == "__main__":
    unittest.main()
