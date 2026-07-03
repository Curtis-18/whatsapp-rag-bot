"""
Turns text into vectors using Voyage AI, Anthropic's recommended embeddings
partner (Claude itself does not generate embeddings).

Two functions, not one, on purpose: Voyage's models are trained to embed a
"document" and a "query" slightly differently for better retrieval accuracy.
Always use embed_documents() when you are loading the knowledge base, and
embed_query() when you are handling an incoming WhatsApp question.
"""
import voyageai
from app.config import VOYAGE_API_KEY, EMBED_MODEL

_client = voyageai.Client(api_key=VOYAGE_API_KEY)


def embed_documents(texts: list[str]) -> list[list[float]]:
    result = _client.embed(texts, model=EMBED_MODEL, input_type="document")
    return result.embeddings


def embed_query(text: str) -> list[float]:
    result = _client.embed([text], model=EMBED_MODEL, input_type="query")
    return result.embeddings[0]
