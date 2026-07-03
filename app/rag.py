"""
The actual "RAG" part: given a question from WhatsApp, find the most
relevant chunks of your knowledge base, then hand them to Claude with strict
instructions to answer only from that material.
"""
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY, CLAUDE_MODEL, TOP_K
from app.embeddings import embed_query
from app.vectorstore import search

_client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a helpful assistant answering questions on WhatsApp using only the reference material provided in each message.

Rules:
- Answer only using the given context. If the context does not contain the answer, say plainly that you do not have that information yet, do not guess.
- Keep replies short and conversational: 2 to 5 sentences, no markdown headers or bullet lists, this is a chat app.
- Never invent facts, numbers, names, or dates that are not present in the context."""


def answer_question(user_message: str) -> str:
    query_vector = embed_query(user_message)
    hits = search(query_vector, top_k=TOP_K)

    if not hits:
        context = "No matching material was found in the knowledge base."
    else:
        context = "\n\n---\n\n".join(
            f"Source: {hit.payload.get('source', 'unknown')}\n{hit.payload.get('text', '')}"
            for hit in hits
        )

    user_prompt = f"Context:\n{context}\n\nQuestion: {user_message}"

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return response.content[0].text
