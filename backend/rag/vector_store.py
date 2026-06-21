"""
rag/vector_store.py — PostgreSQL/pgvector persistence for the RAG pipeline.

Functions
---------
upsert_document   — Insert or update a document row; delete old chunks if hash changed.
insert_chunk      — Insert one chunk + its embedding vector.
vector_search     — Cosine similarity search over chunk embeddings.
list_documents    — Return metadata for all ingested documents.
delete_document   — Hard-delete a document (cascades to chunks via FK).
"""

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Chunk, Document
from rag.chunker import Chunk as RagChunk
from rag.loader import RawDocument

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: int
    content: str
    file_path: str
    heading: str | None
    similarity: float


async def upsert_document(db: AsyncSession, doc: RawDocument) -> tuple[int, bool]:
    """
    Insert a new document row or, if file_path already exists, update it.

    Returns (document_id, chunks_deleted) where chunks_deleted=True means
    the file hash changed and old chunks were removed so new ones can be inserted.
    """
    stmt = (
        pg_insert(Document)
        .values(
            file_path=doc.file_path,
            title=doc.title,
            file_hash=doc.file_hash,
            char_count=doc.char_count,
        )
        .on_conflict_do_update(
            index_elements=["file_path"],
            set_={
                "title": doc.title,
                "char_count": doc.char_count,
                # ingested_at is intentionally NOT updated on re-ingest of same hash
            },
            where=Document.file_hash != doc.file_hash,
        )
        .returning(Document.id, Document.file_hash)
    )
    result = await db.execute(stmt)
    row = result.first()

    if row is None:
        # Conflict happened but WHERE clause prevented update — hash unchanged.
        # Fetch the existing document id.
        existing = await db.execute(
            select(Document.id, Document.file_hash).where(
                Document.file_path == doc.file_path
            )
        )
        row = existing.one()
        if row.file_hash == doc.file_hash:
            await db.commit()
            logger.info("Skipping %s — hash unchanged", doc.file_path)
            return row.id, False  # type: ignore[return-value]

    document_id: int = row.id  # type: ignore[union-attr]

    # Hash has changed (or brand new) — delete stale chunks so they get replaced.
    await db.execute(delete(Chunk).where(Chunk.document_id == document_id))
    await db.commit()
    return document_id, True


async def insert_chunk(
    db: AsyncSession,
    document_id: int,
    chunk: RagChunk,
    embedding: list[float],
) -> None:
    db.add(
        Chunk(
            document_id=document_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
            heading=chunk.heading,
            embedding=embedding,
        )
    )
    await db.flush()  # batch: commit happens after all chunks are inserted


async def vector_search(
    query_vector: list[float],
    db: AsyncSession,
    limit: int = 5,
    min_similarity: float = 0.3,
) -> list[RetrievedChunk]:
    """
    Return the top-k chunks whose cosine similarity to query_vector >= min_similarity.

    pgvector's <=> operator computes cosine distance; 1 - distance = similarity.
    """
    rows = await db.execute(
        text(
            """
            SELECT
                c.id,
                c.content,
                c.heading,
                d.file_path,
                1 - (c.embedding <=> CAST(:qv AS vector)) AS similarity
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
              AND 1 - (c.embedding <=> CAST(:qv AS vector)) >= :min_sim
            ORDER BY c.embedding <=> CAST(:qv AS vector)
            LIMIT :lim
            """
        ),
        {"qv": str(query_vector), "min_sim": min_similarity, "lim": limit},
    )
    return [
        RetrievedChunk(
            chunk_id=row.id,
            content=row.content,
            heading=row.heading,
            file_path=row.file_path,
            similarity=float(row.similarity),
        )
        for row in rows
    ]


async def list_documents(db: AsyncSession) -> list[dict]:
    """Return metadata for every ingested document, newest first."""
    result = await db.execute(
        select(
            Document.id,
            Document.file_path,
            Document.title,
            Document.char_count,
            Document.ingested_at,
        ).order_by(Document.ingested_at.desc())
    )
    docs = []
    for row in result:
        docs.append(
            {
                "id": row.id,
                "file_path": row.file_path,
                "title": row.title,
                "char_count": row.char_count,
                "ingested_at": row.ingested_at.isoformat() if row.ingested_at else None,
            }
        )
    return docs


async def delete_document(db: AsyncSession, document_id: int) -> bool:
    """Delete a document and its chunks. Returns False if document not found."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = result.scalar_one_or_none()
    if doc is None:
        return False
    await db.delete(doc)
    await db.commit()
    return True
