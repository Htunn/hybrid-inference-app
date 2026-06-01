"""
inference.py — /api/chat endpoint

Accepts a unified request payload and streams tokens back as Server-Sent Events
regardless of whether the upstream is local Ollama or Google Gemini.

Unified SSE format (one event per token):
    data: <token text>\n\n

Final event:
    data: [DONE]\n\n
"""

import json
import os
from collections.abc import AsyncIterator

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str  # "user" | "assistant" | "system"
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"user", "assistant", "system"}:
            raise ValueError("role must be 'user', 'assistant', or 'system'")
        return v


class ChatRequest(BaseModel):
    messages: list[Message]

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list[Message]) -> list[Message]:
        if not v:
            raise ValueError("messages list must not be empty")
        last = v[-1]
        if not last.content.strip():
            raise ValueError("last message content must not be blank")
        return v


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=5.0)


async def _stream_ollama(messages: list[Message]) -> AsyncIterator[str]:
    """Stream tokens from the local Ollama server (NDJSON format)."""
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{ollama_base}/api/chat"
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "gemma4:e4b"),
        "messages": [{"role": m.role, "content": m.content} for m in messages],
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
                detail="Cannot reach local Ollama server. Is 'ollama serve' running?",
            ) from exc
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=504, detail="Ollama request timed out.") from exc


async def _stream_gemini(messages: list[Message]) -> AsyncIterator[str]:
    """Stream tokens from Google Gemini API (SSE format)."""
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

    # Map to Gemini content schema
    gemini_contents = []
    for m in messages:
        # Gemini uses "user" / "model" roles
        role = "model" if m.role == "assistant" else m.role
        gemini_contents.append({"role": role, "parts": [{"text": m.content}]})

    payload = {"contents": gemini_contents}

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
                    # Gemini SSE lines: "data: {...}" or empty
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
# Route
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """
    Unified streaming chat endpoint.

    Streams tokens as SSE. The last event is always:
        data: [DONE]
    """
    async def event_stream() -> AsyncIterator[str]:
        provider = os.getenv("INFERENCE_PROVIDER", "ollama")
        upstream = _stream_gemini if provider == "gemini" else _stream_ollama
        async for chunk in upstream(request.messages):
            yield chunk
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering on Render
        },
    )
