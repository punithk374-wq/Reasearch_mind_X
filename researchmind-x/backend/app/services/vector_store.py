import chromadb

from app.services.embedding_service import embed_query, embed_texts
from app.services.retrieval_ranking import cosine_similarity, fuse_rankings, lexical_ranking

_client = chromadb.PersistentClient(path="chroma_db")
_collection = _client.get_or_create_collection(
    name="paper_chunks",
    metadata={"hnsw:space": "cosine"},
)


def _chunk_id(paper_id: int, chunk_id: int) -> str:
    return f"{paper_id}:{chunk_id}"


def index_chunks(paper_id: int, user_id: int, chunks: list[dict]) -> None:
    """chunks: list of {id, text, page_number, section}"""
    if not chunks:
        return

    ids = [_chunk_id(paper_id, c["id"]) for c in chunks]
    texts = [c["text"] for c in chunks]
    vectors = embed_texts(texts)
    metadatas = [
        {
            "paper_id": paper_id,
            "chunk_id": c["id"],
            "user_id": user_id,
            "page_number": c["page_number"],
            "section": c["section"] or "",
        }
        for c in chunks
    ]

    _collection.upsert(ids=ids, embeddings=vectors, documents=texts, metadatas=metadatas)


def delete_paper_vectors(paper_id: int) -> None:
    _collection.delete(where={"paper_id": paper_id})


def search(query: str, user_id: int, top_k: int = 5, paper_id: int | None = None) -> list[dict]:
    where: dict = {"user_id": user_id}
    if paper_id is not None:
        where = {"$and": [{"user_id": user_id}, {"paper_id": paper_id}]}

    # Both candidate sources are scoped before ranking, including BM25 statistics.
    # Read current documents each time so uploads/deletes need no cache invalidation.
    corpus = _collection.get(where=where, include=["documents", "metadatas"])
    if not corpus["ids"]:
        return []
    documents = dict(zip(corpus["ids"], corpus["documents"]))
    metadata = dict(zip(corpus["ids"], corpus["metadatas"]))
    candidate_count = min(len(documents), max(50, top_k * 5))
    query_vector = embed_query(query)
    result = _collection.query(
        query_embeddings=[query_vector],
        n_results=candidate_count,
        where=where,
    )
    dense = [key for key in result["ids"][0] if key in documents]
    lexical = lexical_ranking(query, documents, candidate_count)
    selected = fuse_rankings(dense, lexical, top_k)
    if not selected:
        return []
    # Keep the public score as cosine similarity, not an RRF score or accuracy.
    vectors = _collection.get(ids=selected, where=where, include=["embeddings"])
    embeddings = dict(zip(vectors["ids"], vectors["embeddings"]))
    hits = []
    for key in selected:
        if key not in embeddings:  # A concurrent deletion must not expose stale text.
            continue
        meta = metadata[key]
        hits.append(
            {
                "chunk_id": meta["chunk_id"],
                "paper_id": meta["paper_id"],
                "page_number": meta["page_number"],
                "section": meta["section"] or None,
                "text": documents[key],
                "score": round(cosine_similarity(query_vector, embeddings[key]), 4),
            }
        )
    return hits
