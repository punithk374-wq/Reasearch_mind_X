import chromadb

from app.services.embedding_service import embed_query, embed_texts

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

    result = _collection.query(
        query_embeddings=[embed_query(query)],
        n_results=top_k,
        where=where,
    )

    if not result["ids"][0]:
        return []

    hits = []
    for i in range(len(result["ids"][0])):
        meta = result["metadatas"][0][i]
        distance = result["distances"][0][i]
        hits.append(
            {
                "chunk_id": meta["chunk_id"],
                "paper_id": meta["paper_id"],
                "page_number": meta["page_number"],
                "section": meta["section"] or None,
                "text": result["documents"][0][i],
                "score": round(1 - distance, 4),  # cosine distance -> similarity
            }
        )
    return hits