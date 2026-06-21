"""
routers/rag.py — RAG pipeline endpoints.

Routes
------
POST   /api/rag/ingest              Upload and ingest a document (.md/.txt/.pdf)
POST   /api/rag/query               Ask a question; streams SSE tokens + sources
GET    /api/rag/documents           List all ingested documents
DELETE /api/rag/documents/{doc_id}  Delete a document and its chunks

SSE format (matches /api/chat so the frontend parser is shared):
  Each token:   data: "<token>"\n\n
  Sources event: data: {"type":"sources","sources":["file.md",...]}\n\n
  Final:        data: [DONE]\n\n
"""

import json
import logging
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import get_session
from rag.chunker import split_document
from rag.embedder import EmbeddingProvider
from rag.loader import load_upload
from rag.prompt_builder import SYSTEM_PROMPT, build_prompt
from rag.vector_store import (
    delete_document,
    insert_chunk,
    list_documents,
    upsert_document,
    vector_search,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rag"])

TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4096)
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.3, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Dependency — embedder stored in app.state at lifespan startup
# ---------------------------------------------------------------------------


def _get_embedder(request: Request) -> EmbeddingProvider:
    embedder: EmbeddingProvider | None = getattr(request.app.state, "embedder", None)
    if embedder is None:
        raise HTTPException(status_code=503, detail="Embedding model is not ready yet.")
    return embedder


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


@router.post("/ingest")
async def ingest(
    file: UploadFile,
    db: AsyncSession = Depends(get_session),
    embedder: EmbeddingProvider = Depends(_get_embedder),
) -> dict:
    """
    Upload a .md, .txt, or .pdf file and store its chunks in the vector store.

    Returns the number of chunks created. If the file hash hasn't changed since
    the last ingest, the call is a no-op and chunks_created=0.
    """
    if file.filename is None:
        raise HTTPException(status_code=400, detail="File name is required.")

    raw_bytes = await file.read()

    try:
        doc = load_upload(raw_bytes, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_id, changed = await upsert_document(db, doc)

    if not changed:
        return {
            "status": "skipped",
            "message": "File content is unchanged; skipping re-ingestion.",
            "document_id": document_id,
            "file_name": file.filename,
            "chunks_created": 0,
        }

    chunks = split_document(doc)
    if not chunks:
        return {
            "status": "ok",
            "document_id": document_id,
            "file_name": file.filename,
            "chunks_created": 0,
        }

    texts = [c.content for c in chunks]
    embeddings = await embedder.embed(texts)

    for chunk, embedding in zip(chunks, embeddings, strict=True):
        await insert_chunk(db, document_id, chunk, embedding)
    await db.commit()

    logger.info(
        "Ingested %s → document_id=%d, chunks=%d",
        file.filename,
        document_id,
        len(chunks),
    )
    return {
        "status": "ok",
        "document_id": document_id,
        "file_name": file.filename,
        "chunks_created": len(chunks),
    }


# ---------------------------------------------------------------------------
# Query — SSE stream
# ---------------------------------------------------------------------------


@router.post("/query")
async def query(
    req: QueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    embedder: EmbeddingProvider = Depends(_get_embedder),
) -> StreamingResponse:
    """
    Ask a question over the ingested knowledge base.

    Streams tokens via SSE. The second-to-last event carries retrieved sources:
        data: {"type":"sources","sources":["file.md", ...]}\n\n
    The final event is:
        data: [DONE]\n\n
    """
    query_vector = await embedder.embed_one(req.question)
    chunks = await vector_search(
        query_vector, db, limit=req.top_k, min_similarity=req.min_similarity
    )

    sources: list[str] = list(
        dict.fromkeys(c.file_path for c in chunks)  # deduplicated, order-preserving
    )

    if not chunks:
        async def _no_content() -> AsyncIterator[str]:
            yield f"data: {json.dumps('No relevant content found for this question.')}\n\n"
            yield f"data: {json.dumps({'type': 'sources', 'sources': []})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            _no_content(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    user_message = f"{SYSTEM_PROMPT}\n\n{build_prompt(req.question, chunks)}"

    async def event_stream() -> AsyncIterator[str]:
        provider = os.getenv("INFERENCE_PROVIDER", "ollama")
        async for chunk in _stream_rag(provider, user_message):
            yield chunk
        yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _stream_rag(provider: str, user_message: str) -> AsyncIterator[str]:
    """Stream tokens for a single user message using the configured LLM provider."""
    if provider == "gemini":
        async for token_event in _stream_gemini_rag(user_message):
            yield token_event
    else:
        async for token_event in _stream_ollama_rag(user_message):
            yield token_event


async def _stream_ollama_rag(user_message: str) -> AsyncIterator[str]:
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{ollama_base}/api/chat"
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=f"Ollama returned {resp.status_code}: {body.decode()[:200]}",
                    )
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield f"data: {json.dumps(token)}\n\n"
                    if chunk.get("done"):
                        break
        except httpx.ConnectError as exc:
            raise HTTPException(
                status_code=503,
                detail="Cannot reach local Ollama server.",
            ) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Ollama request timed out.") from exc


async def _stream_gemini_rag(user_message: str) -> AsyncIterator[str]:
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY is not configured on the server.",
        )
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:streamGenerateContent?alt=sse&key={api_key}"
    )
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=f"Gemini API returned {resp.status_code}.",
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    try:
                        token = chunk["candidates"][0]["content"]["parts"][0]["text"]
                    except (KeyError, IndexError):
                        continue
                    if token:
                        yield f"data: {json.dumps(token)}\n\n"
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Gemini request timed out.") from exc


# ---------------------------------------------------------------------------
# Document management
# ---------------------------------------------------------------------------


@router.get("/documents")
async def get_documents(db: AsyncSession = Depends(get_session)) -> list[dict]:
    """Return metadata for all ingested documents."""
    return await list_documents(db)


@router.delete("/documents/{doc_id}")
async def remove_document(
    doc_id: int,
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a document and all its chunks from the vector store."""
    deleted = await delete_document(db, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found.")
    return {"status": "deleted", "document_id": doc_id}
