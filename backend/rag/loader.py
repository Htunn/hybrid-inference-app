"""
rag/loader.py — File upload → RawDocument.

Supports three MIME types:
  - text/markdown (.md)   — read as UTF-8
  - text/plain    (.txt)  — read as UTF-8
  - application/pdf (.pdf) — extract text layer via pypdf

The SHA-256 hash is computed over the raw bytes so that the ingestion
pipeline can skip re-embedding unchanged files.
"""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Maximum file size accepted by the ingestion endpoint (10 MB)
MAX_FILE_BYTES = 10 * 1024 * 1024


@dataclass
class RawDocument:
    file_path: str       # Relative filename used as the unique key in `documents`
    content: str         # Full extracted text
    file_hash: str       # SHA-256 hex digest of the raw bytes
    title: str | None    # First H1 heading, or None
    char_count: int


def load_upload(file_bytes: bytes, filename: str) -> RawDocument:
    """
    Convert uploaded file bytes into a RawDocument.

    Raises ValueError for unsupported extensions or files that are too large.
    """
    if len(file_bytes) > MAX_FILE_BYTES:
        raise ValueError(
            f"File exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MB size limit."
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in {".md", ".txt", ".pdf"}:
        raise ValueError(
            f"Unsupported file type '{suffix}'. Supported: .md, .txt, .pdf"
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    if suffix == ".pdf":
        content = _extract_pdf_text(file_bytes, filename)
    else:
        content = file_bytes.decode("utf-8", errors="replace")

    title = _extract_h1(content) or Path(filename).stem
    logger.info(
        "Loaded %s — %d chars, hash=%s…", filename, len(content), file_hash[:8]
    )
    return RawDocument(
        file_path=filename,
        content=content,
        file_hash=file_hash,
        title=title,
        char_count=len(content),
    )


def _extract_pdf_text(data: bytes, filename: str) -> str:
    """Extract all text from PDF pages using pypdf."""
    try:
        import io

        from pypdf import PdfReader  # type: ignore[import]

        reader = PdfReader(io.BytesIO(data))
        pages = []
        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)
        return "\n\n".join(pages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF text extraction failed for %s: %s", filename, exc)
        return ""


def _extract_h1(content: str) -> str | None:
    """Return the text of the first Markdown H1 heading, or None."""
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.lstrip("# ").strip()
    return None
