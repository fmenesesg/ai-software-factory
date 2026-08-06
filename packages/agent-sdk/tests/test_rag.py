"""RAG embed+query path tests with in-memory fake (task 6.3)."""

from __future__ import annotations

import pytest

from agent_sdk.rag import HashingEmbedder, InMemoryVectorStore, PgVectorStore, RagDocument, RagRetriever


def test_rag_index_and_retrieve() -> None:
    store = InMemoryVectorStore()
    retriever = RagRetriever(store, HashingEmbedder(dims=32))
    docs = [
        RagDocument(doc_id="adr-009", text="RAG uses PostgreSQL pgvector for MVP retrieval", metadata={"kind": "adr"}),
        RagDocument(doc_id="adr-003", text="Live Granite is primary; emergency fallback only", metadata={"kind": "adr"}),
        RagDocument(doc_id="openapi", text="Orders and inventory REST API health endpoint", metadata={"kind": "openapi"}),
    ]
    assert retriever.index(docs) == 3
    hits = retriever.retrieve("pgvector retrieval postgres", top_k=2)
    assert hits
    assert hits[0].doc_id == "adr-009"
    assert hits[0].score > 0


def test_pgvector_requires_dsn() -> None:
    with pytest.raises(ValueError, match="DSN"):
        PgVectorStore("")
