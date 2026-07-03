"""
Loads every file in knowledge_base/ into Qdrant, as embeddings.
Run this once to build the knowledge base, and re-run any time you add or
change a document.

Usage:
    python -m scripts.ingest
"""
import glob
import os
import uuid

from app.embeddings import embed_documents
from app.vectorstore import recreate_collection, upsert_chunks

CHUNK_SIZE = 800      # characters per chunk, not tokens, kept simple on purpose
CHUNK_OVERLAP = 150   # overlap so an answer split across a chunk boundary isn't lost
BATCH_SIZE = 100       # embed in batches so one giant knowledge base doesn't hit request limits


def read_text(path: str) -> str:
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def main() -> dict:
    files = [f for f in glob.glob("knowledge_base/**/*", recursive=True) if os.path.isfile(f)]
    if not files:
        message = "No files found in knowledge_base/. Add .txt, .md or .pdf files and re-run."
        print(message)
        return {"files": 0, "chunks": 0, "message": message}

    all_chunks, all_sources = [], []
    for path in files:
        text = read_text(path)
        chunks = chunk_text(text)
        all_chunks.extend(chunks)
        all_sources.extend([os.path.basename(path)] * len(chunks))
        print(f"{path}: {len(chunks)} chunks")

    print(f"Embedding {len(all_chunks)} chunks with Voyage AI ({BATCH_SIZE} at a time)...")
    all_vectors = []
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        all_vectors.extend(embed_documents(batch))
        print(f"  embedded {min(i + BATCH_SIZE, len(all_chunks))}/{len(all_chunks)}")

    recreate_collection(vector_size=len(all_vectors[0]))

    ids = [str(uuid.uuid4()) for _ in all_chunks]
    payloads = [{"text": c, "source": s} for c, s in zip(all_chunks, all_sources)]
    upsert_chunks(ids, all_vectors, payloads)

    message = f"Done. {len(all_chunks)} chunks from {len(files)} files stored in Qdrant."
    print(message)
    return {"files": len(files), "chunks": len(all_chunks), "message": message}


if __name__ == "__main__":
    main()
