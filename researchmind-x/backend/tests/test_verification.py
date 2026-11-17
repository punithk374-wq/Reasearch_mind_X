"""Deterministic regression tests; no API calls or database access."""
import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SERVICE = Path(__file__).resolve().parents[1] / "app/services/verification_service.py"
GAP = {
    "title": "A fixture gap", "description": "A claim for test purposes",
    "evidence": "Fixture evidence", "supporting_paper_ids": [11, 12],
}


def load_verifier(response, available=(11, 12)):
    generate = Mock(return_value=SimpleNamespace(text=json.dumps(response)))
    llm = ModuleType("app.services.llm_service")
    llm._client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    llm.MODEL = "test-model"
    vectors = ModuleType("app.services.vector_store")
    vectors.search = lambda query, user_id, top_k, paper_id: (
        [{"paper_id": paper_id, "page_number": 2, "section": "limitations", "text": "Fixture text."}]
        if paper_id in available else []
    )
    spec = importlib.util.spec_from_file_location("verifier_under_test", SERVICE)
    module = importlib.util.module_from_spec(spec)
    with patch.dict("sys.modules", {
        "app.services.llm_service": llm, "app.services.vector_store": vectors,
    }):
        spec.loader.exec_module(module)
    return module, generate


def result(verdict="supported", ids=None):
    return {"index": 0, "verdict": verdict, "supported_paper_ids": [11, 12] if ids is None else ids,
            "reason": "Model explanation."}


class VerificationTests(unittest.TestCase):
    def check(self, response, available=(11, 12)):
        module, _ = load_verifier(response, available)
        return module.verify_gaps_batch([GAP], user_id=7)[0]

    def test_full_support_requires_all_cited_papers(self):
        item = self.check({"results": [result(ids=[11])]})
        self.assertEqual(item["verdict"], "partial")
        self.assertEqual(item["supported_paper_ids"], [11])

    def test_paper_without_a_passage_cannot_be_verified(self):
        item = self.check({"results": [result()]}, available=(11,))
        self.assertEqual(item["verdict"], "partial")
        self.assertEqual(item["supported_paper_ids"], [11])

    def test_supported_without_supported_ids_is_unverified(self):
        item = self.check({"results": [result(ids=[])]})
        self.assertEqual(item["verdict"], "unverified")
        self.assertEqual(item["supported_paper_ids"], [])

    def test_duplicate_result_index_is_ambiguous(self):
        item = self.check({"results": [result(), result("unsupported", [])]})
        self.assertEqual(item["verdict"], "unverified")

    def test_bad_json_shapes_do_not_crash(self):
        for response in [[], None, {"results": None}, {"results": [None]},
                         {"results": [result(ids=None) | {"supported_paper_ids": None}]}]:
            with self.subTest(response=response):
                self.assertEqual(self.check(response)["verdict"], "unverified")

    def test_unknown_verdict_cannot_confirm_any_paper(self):
        item = self.check({"results": [result("unknown")]})
        self.assertEqual(item["verdict"], "unverified")
        self.assertEqual(item["supported_paper_ids"], [])

    def test_no_passages_skips_model_call(self):
        module, generate = load_verifier({"results": [result()]}, available=())
        item = module.verify_gaps_batch([GAP], user_id=7)[0]
        self.assertEqual(item["verdict"], "unsupported")
        generate.assert_not_called()

    def test_valid_support_is_preserved(self):
        item = self.check({"results": [result()]})
        self.assertEqual(item["verdict"], "supported")
        self.assertEqual(item["supported_paper_ids"], [11, 12])

    def test_single_gap_uses_the_same_checks(self):
        module, _ = load_verifier({"results": [result(ids=[11])]})
        self.assertEqual(module.verify_gap(GAP, user_id=7)["verdict"], "partial")


if __name__ == "__main__":
    unittest.main()
