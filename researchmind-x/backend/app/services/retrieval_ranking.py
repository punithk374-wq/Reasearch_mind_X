"""Dependency-free lexical ranking and reciprocal-rank fusion.

No evaluation questions, labels, paper IDs or expected answers enter ranking.
"""
from collections import Counter
import math
import re
import unicodedata


STOP_WORDS = frozenset('a an and are as at be been by can did do does for from had has have how in into is it its of on or that the their these they this to was were what when where which who why will with would'.split())


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize('NFKC', text).casefold()
    return [t for t in re.findall(r'[^\W_]+', text) if t not in STOP_WORDS]


def lexical_ranking(query: str, documents: dict[str, str], limit: int) -> list[str]:
    """BM25 with k1=1.5, b=0.75; exclude documents with no lexical matches."""
    terms = sorted(set(tokens(query)))
    if not terms or not documents:
        return []
    counts = {key: Counter(tokens(text)) for key, text in documents.items()}
    lengths = {key: sum(value.values()) for key, value in counts.items()}
    average = sum(lengths.values()) / len(counts) or 1.0
    frequencies = Counter(t for value in counts.values() for t in terms if t in value)
    scores = {}
    for key, value in counts.items():
        score = 0.0
        for term in terms:
            tf = value[term]
            if not tf:
                continue
            df = frequencies[term]
            idf = math.log(1 + (len(counts) - df + 0.5) / (df + 0.5))
            score += idf * tf * 2.5 / (tf + 1.5 * (0.25 + 0.75 * lengths[key] / average))
        if score > 0:
            scores[key] = score
    return sorted(scores, key=lambda key: (-scores[key], key))[:limit]


def fuse_rankings(dense: list[str], lexical: list[str], limit: int) -> list[str]:
    """Equal-weight RRF (constant 60), stable ties, no score-scale assumptions."""
    scores = {}
    for ranking in (dense, lexical):
        for rank, key in enumerate(dict.fromkeys(ranking), 1):
            scores[key] = scores.get(key, 0.0) + 1.0 / (60 + rank)
    dense_ranks = {key: rank for rank, key in enumerate(dense)}
    return sorted(scores, key=lambda key: (-scores[key], dense_ranks.get(key, len(dense)), key))[:limit]


def cosine_similarity(left, right) -> float:
    if len(left) != len(right):
        raise ValueError('Stored embedding dimensions differ; reindex using the current model')
    denominator = math.sqrt(sum(float(x) ** 2 for x in left) * sum(float(x) ** 2 for x in right))
    return sum(float(x) * float(y) for x, y in zip(left, right)) / denominator if denominator else 0.0
