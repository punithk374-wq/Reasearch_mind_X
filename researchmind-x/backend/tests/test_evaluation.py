import contextlib
import io
import unittest

from eval_common import ApiError, chunk_fingerprint
from eval_retrieval import run_evaluation, score_hits, validate_corpus, validate_dataset


GOLD = [{"paper_id": 1, "chunk_id": 10}, {"paper_id": 1, "chunk_id": 11}]


class EvaluationTests(unittest.TestCase):
    def test_known_rankings_and_missing_results(self):
        scores = score_hits([{"paper_id": 2, "chunk_id": 10}, GOLD[0]], GOLD)
        self.assertEqual(scores["hit@1"], 0)
        self.assertEqual(scores["hit@3"], 1)
        self.assertEqual(scores["precision@5"], 0.2)
        self.assertEqual(scores["recall@5"], 0.5)
        self.assertEqual(scores["mrr@5"], 0.5)

    def test_duplicate_hits_do_not_inflate_metrics(self):
        scores = score_hits([GOLD[0]] * 5, GOLD)
        self.assertEqual(scores["precision@5"], 0.2)
        self.assertEqual(scores["recall@5"], 0.5)

    def test_no_hits_score_zero(self):
        self.assertTrue(all(value == 0 for value in score_hits([], GOLD).values()))

    def test_corpus_fingerprint_detects_text_or_page_changes(self):
        first = [{"id": 1, "page_number": 1, "section": "method", "text": "Evidence"}]
        second = [{**first[0], "page_number": 2}]
        self.assertNotEqual(chunk_fingerprint(first), chunk_fingerprint(second))

    def test_example_labels_are_rejected(self):
        data = {"schema_version": 1, "paper_fingerprints": {"1": "a" * 64},
                "items": [{"id": "Q1", "question": "A question", "answerable": True,
                           "relevant_chunks": [{"paper_id": None, "chunk_id": None}]}]}
        with self.assertRaises(ValueError):
            validate_dataset(data)

    def test_changed_corpus_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_corpus({"paper_fingerprints": {"1": "a" * 64}},
                            [{"paper_id": 1, "fingerprint": "b" * 64}])

    def test_failed_requests_count_in_average(self):
        class Client:
            def request(self, path, data):
                if data["query"] == "failure":
                    raise ApiError("Intentional fixture failure")
                return [GOLD[0]]
        items = [{"id": str(i), "question": question, "answerable": True, "relevant_chunks": [GOLD[0]]}
                 for i, question in enumerate(["success", "failure"])]
        with contextlib.redirect_stdout(io.StringIO()):
            report = run_evaluation(Client(), items)
        self.assertEqual(report["summary"]["retrieval_metrics"]["hit@1"], 0.5)
        self.assertEqual(report["summary"]["retrieval_failures"], 1)


if __name__ == "__main__":
    unittest.main()
