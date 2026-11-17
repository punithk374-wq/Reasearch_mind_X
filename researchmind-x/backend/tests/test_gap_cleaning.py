import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


class GapCleaningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        llm = ModuleType("app.services.llm_service")
        llm._client, llm.MODEL = SimpleNamespace(), "fixture-model"
        spec = importlib.util.spec_from_file_location("gap_service_under_test", Path(__file__).resolve().parents[1] / "app/services/gap_service.py")
        cls.service = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", {"app.services.llm_service": llm}):
            spec.loader.exec_module(cls.service)

    def test_malformed_payloads_do_not_crash(self):
        for payload in [None, [], {"gaps": None}, {"gaps": [None]}, {"gaps": [{"type": []}]}]:
            with self.subTest(payload=payload):
                self.assertEqual(self.service._clean(payload, {1})["gaps"], [])

    def test_unknown_sources_and_boolean_ids_are_removed(self):
        gap = {"type": "recurring_limitation", "title": "Fixture", "description": "Description",
               "evidence": "Evidence", "research_question": "Question?", "supporting_paper_ids": [True, 1, 1, 99]}
        clean = self.service._clean({"gaps": [gap]}, {1})
        self.assertEqual(clean["gaps"][0]["supporting_paper_ids"], [1])
        gap["evidence"] = []
        self.assertEqual(self.service._clean({"gaps": [gap]}, {1})["gaps"], [])


if __name__ == "__main__":
    unittest.main()
