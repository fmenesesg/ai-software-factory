"""RAG store abstractions — PostgreSQL+pgvector with in-memory fake (ADR-009)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol, Sequence


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


@dataclass(frozen=True, slots=True)
class RagDocument:
    doc_id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RagHit:
    doc_id: str
    text: str
    score: float
    metadata: dict[str, str]


class EmbeddingModel(Protocol):
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Deterministic fake embedder for tests (no external model required)."""

    def __init__(self, dims: int = 32) -> None:
        self.dims = dims

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dims
            for i, ch in enumerate(text.encode("utf-8")):
                vec[i % self.dims] += (ch % 31) / 31.0
            # L2 normalize
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class VectorStore(Protocol):
    def upsert(self, documents: Sequence[RagDocument], vectors: Sequence[Sequence[float]]) -> int: ...

    def query(self, vector: Sequence[float], *, top_k: int = 5) -> list[RagHit]: ...


class InMemoryVectorStore:
    """Fake pgvector-shaped store for Architect/PM retrieval unit tests."""

    def __init__(self) -> None:
        self._rows: list[tuple[RagDocument, list[float]]] = []

    def upsert(self, documents: Sequence[RagDocument], vectors: Sequence[Sequence[float]]) -> int:
        if len(documents) != len(vectors):
            raise ValueError("documents and vectors length mismatch")
        for doc, vec in zip(documents, vectors, strict=True):
            self._rows = [(d, v) for d, v in self._rows if d.doc_id != doc.doc_id]
            self._rows.append((doc, list(vec)))
        return len(documents)

    def query(self, vector: Sequence[float], *, top_k: int = 5) -> list[RagHit]:
        scored = [
            RagHit(
                doc_id=doc.doc_id,
                text=doc.text,
                score=_cosine(vector, vec),
                metadata=dict(doc.metadata),
            )
            for doc, vec in self._rows
        ]
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[: max(1, top_k)]


class PgVectorStore:
    """
    Thin pgvector adapter.

    Requires optional deps (psycopg). Without a live DSN, callers should use
    InMemoryVectorStore. This class validates SQL shape and fails closed when
    the driver/DSN is unavailable — embed+query path remains testable via fake.
    """

    def __init__(self, dsn: str, *, table: str = "asf_rag_chunks", dims: int = 32) -> None:
        if not dsn:
            raise ValueError("CHECKPOINT/RAG DSN required for PgVectorStore")
        self.dsn = dsn
        self.table = table
        self.dims = dims
        self._conn = None

    def connect(self) -> None:
        try:
            import psycopg
        except ImportError as exc:  # pragma: no cover — optional path
            raise RuntimeError("psycopg required for live pgvector") from exc
        self._conn = psycopg.connect(self.dsn)

    def ensure_schema(self) -> None:
        if self._conn is None:
            raise RuntimeError("not connected")
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.table} (
                  doc_id TEXT PRIMARY KEY,
                  text TEXT NOT NULL,
                  metadata JSONB DEFAULT '{{}}'::jsonb,
                  embedding vector({self.dims})
                )
                """
            )
        self._conn.commit()

    def upsert(self, documents: Sequence[RagDocument], vectors: Sequence[Sequence[float]]) -> int:
        if self._conn is None:
            raise RuntimeError("not connected")
        if len(documents) != len(vectors):
            raise ValueError("documents and vectors length mismatch")
        import json

        with self._conn.cursor() as cur:
            for doc, vec in zip(documents, vectors, strict=True):
                cur.execute(
                    f"""
                    INSERT INTO {self.table} (doc_id, text, metadata, embedding)
                    VALUES (%s, %s, %s::jsonb, %s::vector)
                    ON CONFLICT (doc_id) DO UPDATE
                      SET text = EXCLUDED.text,
                          metadata = EXCLUDED.metadata,
                          embedding = EXCLUDED.embedding
                    """,
                    (doc.doc_id, doc.text, json.dumps(doc.metadata), list(vec)),
                )
        self._conn.commit()
        return len(documents)

    def query(self, vector: Sequence[float], *, top_k: int = 5) -> list[RagHit]:
        if self._conn is None:
            raise RuntimeError("not connected")
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT doc_id, text, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM {self.table}
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (list(vector), list(vector), top_k),
            )
            rows = cur.fetchall()
        hits: list[RagHit] = []
        for doc_id, text, metadata, score in rows:
            meta = dict(metadata) if isinstance(metadata, dict) else {}
            hits.append(RagHit(doc_id=doc_id, text=text, score=float(score), metadata=meta))
        return hits


class RagRetriever:
    """Embed + query path for Architect/PM retrieval."""

    def __init__(self, store: VectorStore, embedder: EmbeddingModel | None = None) -> None:
        self.store = store
        self.embedder = embedder or HashingEmbedder()

    def index(self, documents: Sequence[RagDocument]) -> int:
        vectors = self.embedder.embed([d.text for d in documents])
        return self.store.upsert(documents, vectors)

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RagHit]:
        vector = self.embedder.embed([query])[0]
        return self.store.query(vector, top_k=top_k)
