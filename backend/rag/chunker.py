"""
rag/chunker.py — Text → list[Chunk] with heading-aware splitting.

Strategy (from the blog):
  - Markdown / text: split at ## headings first.
    Sections that exceed max_tokens fall back to sentence-boundary splitting
    with a configurable overlap window.
  - PDF (plain text after extraction): same algorithm — no special casing needed
    because pypdf gives us plain text.

Token count is approximated by word count (no tokenizer dependency). This is
accurate enough for chunk sizing; exact token counts aren't needed here.
"""

import re
from dataclasses import dataclass

from rag.loader import RawDocument


@dataclass
class Chunk:
    content: str
    chunk_index: int
    token_count: int
    heading: str | None   # Nearest heading above this chunk


def split_document(
    doc: RawDocument,
    max_tokens: int = 400,
    overlap: int = 50,
) -> list[Chunk]:
    """Split a RawDocument into retrieval chunks."""
    return _split_text(doc.content, max_tokens=max_tokens, overlap=overlap)


def _split_text(text: str, max_tokens: int, overlap: int) -> list[Chunk]:
    # Split at level-1 or level-2 markdown headings.  Using a lookahead so
    # the heading line is kept at the start of each section.
    sections = re.split(r"(?=^#{1,2} )", text, flags=re.MULTILINE)
    chunks: list[Chunk] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        heading = _extract_heading(section)
        tokens = _count_tokens(section)

        if tokens <= max_tokens:
            chunks.append(
                Chunk(
                    content=section,
                    chunk_index=len(chunks),
                    token_count=tokens,
                    heading=heading,
                )
            )
        else:
            # Section is too long — split at sentence boundaries with overlap
            sub_chunks = _sentence_split(section, max_tokens, overlap)
            for sub in sub_chunks:
                chunks.append(
                    Chunk(
                        content=sub,
                        chunk_index=len(chunks),
                        token_count=_count_tokens(sub),
                        heading=heading,
                    )
                )

    return chunks


def _sentence_split(text: str, max_tokens: int, overlap: int) -> list[str]:
    """Split text at sentence boundaries, yielding windows with overlap."""
    # Naive sentence splitter — split on ". ", "! ", "? ", or newlines
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    result: list[str] = []
    window: list[str] = []
    window_tokens = 0

    for sentence in sentences:
        s_tokens = _count_tokens(sentence)

        if window_tokens + s_tokens > max_tokens and window:
            result.append(" ".join(window))
            # Keep the overlap portion of the window
            kept: list[str] = []
            kept_tokens = 0
            for s in reversed(window):
                if kept_tokens + _count_tokens(s) > overlap:
                    break
                kept.insert(0, s)
                kept_tokens += _count_tokens(s)
            window = kept
            window_tokens = kept_tokens

        window.append(sentence)
        window_tokens += s_tokens

    if window:
        result.append(" ".join(window))

    return result


def _count_tokens(text: str) -> int:
    """Approximate token count via word count (fast, no tokenizer dependency)."""
    return len(text.split())


def _extract_heading(section: str) -> str | None:
    """Return the first heading line from a section, stripped of # characters."""
    first_line = section.splitlines()[0] if section.splitlines() else ""
    if first_line.startswith("#"):
        return first_line.lstrip("#").strip()
    return None
