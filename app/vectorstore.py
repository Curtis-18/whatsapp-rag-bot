"""
Thin wrapper around Qdrant so the rest of the app never touches the client
library directly. Uses query_points(), the current retrieval method: the
older client.search() call was removed from qdrant-client in 2025, so any
tutorial code you find online using .search() will error out on a fresh
install.
"""
from qdrant_client import QdrantClient, models
from app.config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def collection_exists() -> bool:
    existing = [c.name for c in client.get_collections().collections]
    return QDRANT_COLLECTION in existing


def recreate_collection(vector_size: int) -> None:
    """
    Wipe and recreate the collection. Used by ingestion so that re-running it
    (e.g. after you edit knowledge_base/ and redeploy) fully replaces the old
    data instead of just adding to it.
    """
    if collection_exists():
        client.delete_collection(QDRANT_COLLECTION)
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(
            size=vector_size, distance=models.Distance.COSINE
        ),
    )


def upsert_chunks(ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> None:
    points = [
        models.PointStruct(id=i, vector=v, payload=p)
        for i, v, p in zip(ids, vectors, payloads)
    ]
    client.upsert(collection_name=QDRANT_COLLECTION, points=points, wait=True)


def search(query_vector: list[float], top_k: int):
    result = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        with_payload=True,
    )
    return result.points
