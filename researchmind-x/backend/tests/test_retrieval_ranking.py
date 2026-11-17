import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app.services.retrieval_ranking import cosine_similarity, fuse_rankings, lexical_ranking, tokens


class RankingTests(unittest.TestCase):
    def test_rare_term_passage_beats_generic_discussion(self):
        docs = {'a': 'General model evaluation and dataset discussions.',
                'b': 'Annotation disagreements were resolved through discussion.',
                'c': 'Model evaluation uses a dataset.'}
        self.assertEqual(lexical_ranking('How were annotation disagreements resolved?', docs, 3), ['b'])

    def test_unicode_and_punctuation(self):
        self.assertEqual(tokens('ＡＩ—Trust, 42.9%'), ['ai', 'trust', '42', '9'])

    def test_no_matches_do_not_create_arbitrary_lexical_candidates(self):
        self.assertEqual(lexical_ranking('the and', {'a': 'evidence'}, 5), [])
        self.assertEqual(lexical_ranking('absent', {'a': 'evidence'}, 5), [])
        self.assertEqual(lexical_ranking('evidence', {}, 5), [])

    def test_both_rankings_promote_shared_candidate(self):
        self.assertEqual(fuse_rankings(['generic', 'evidence'], ['evidence'], 2), ['evidence', 'generic'])

    def test_dense_fallback_and_duplicate_protection(self):
        self.assertEqual(fuse_rankings(['b', 'a'], [], 2), ['b', 'a'])
        self.assertEqual(fuse_rankings(['b', 'b', 'a'], ['a'], 2), ['a', 'b'])

    def test_cosine_is_not_fusion_score(self):
        self.assertAlmostEqual(cosine_similarity([2, 0], [3, 4]), 0.6)
        self.assertEqual(cosine_similarity([0, 0], [1, 1]), 0)
        with self.assertRaises(ValueError):
            cosine_similarity([1], [1, 2])


class SearchIntegrationTests(unittest.TestCase):
    def load_service(self, rows):
        self.rows = rows
        collection = Mock()
        self.filters = []

        def matches(meta, where):
            if '$and' in where:
                return all(matches(meta, item) for item in where['$and'])
            return all(meta.get(key) == value for key, value in where.items())

        def get(where, include, ids=None):
            self.filters.append(where)
            filtered = [r for r in rows if matches(r['meta'], where) and (ids is None or r['id'] in ids)]
            return {'ids': [r['id'] for r in filtered], 'documents': [r['text'] for r in filtered],
                    'metadatas': [r['meta'] for r in filtered], 'embeddings': [r['vector'] for r in filtered]}

        def query(query_embeddings, n_results, where):
            self.filters.append(where)
            filtered = [r for r in rows if matches(r['meta'], where)][:n_results]
            return {'ids': [[r['id'] for r in filtered]]}

        collection.get.side_effect, collection.query.side_effect = get, query
        chroma = ModuleType('chromadb')
        chroma.PersistentClient = Mock(return_value=SimpleNamespace(get_or_create_collection=lambda **kwargs: collection))
        embedding = ModuleType('app.services.embedding_service')
        embedding.embed_query = Mock(return_value=[1, 0])
        embedding.embed_texts = Mock()
        path = Path(__file__).resolve().parents[1] / 'app/services/vector_store.py'
        spec = importlib.util.spec_from_file_location('tested_vector_store', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'chromadb': chroma, 'app.services.embedding_service': embedding}):
            spec.loader.exec_module(module)
        return module, embedding

    @staticmethod
    def row(cid, text, user=1, paper=1, vector=(1, 0)):
        return {'id': f'{paper}:{cid}', 'text': text, 'vector': vector,
                'meta': {'chunk_id': cid, 'paper_id': paper, 'user_id': user, 'page_number': 1, 'section': ''}}

    def test_keyword_evidence_promoted_with_real_cosine_score(self):
        service, _ = self.load_service([self.row(1, 'General evaluation discussion.'),
            self.row(2, 'Annotation disagreements resolved through discussion.', vector=(0.6, 0.8))])
        hits = service.search('annotation disagreements resolved', 1, top_k=1)
        self.assertEqual(hits[0]['chunk_id'], 2)
        self.assertEqual(hits[0]['score'], 0.6)

    def test_user_and_paper_scope_applied_to_every_read(self):
        service, _ = self.load_service([self.row(1, 'private exact evidence', user=2),
            self.row(2, 'private exact evidence', paper=2), self.row(3, 'public evidence')])
        hits = service.search('private exact evidence', 1, top_k=5, paper_id=1)
        self.assertEqual([h['chunk_id'] for h in hits], [3])
        self.assertTrue(all(f == {'$and': [{'user_id': 1}, {'paper_id': 1}]} for f in self.filters))

    def test_empty_user_corpus_skips_embedding(self):
        service, embedding = self.load_service([self.row(1, 'Other user', user=2)])
        self.assertEqual(service.search('question', 1), [])
        embedding.embed_query.assert_not_called()

    def test_new_search_reflects_deletion(self):
        rows = [self.row(1, 'unique evidence')]
        service, _ = self.load_service(rows)
        self.assertEqual(len(service.search('unique', 1)), 1)
        rows.clear()
        self.assertEqual(service.search('unique', 1), [])
