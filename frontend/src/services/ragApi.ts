/**
 * ragApi.ts — RAG pipeline service layer.
 *
 * Mirrors the SSE parsing logic from api.ts.  The only difference is that the
 * RAG query stream includes one extra event before [DONE]:
 *   data: {"type":"sources","sources":["file.md", ...]}\n\n
 *
 * streamRagQuery() yields plain text tokens and resolves the returned promise
 * with the final sources list once the stream closes.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface RagDocument {
  id: number;
  file_path: string;
  title: string | null;
  char_count: number | null;
  ingested_at: string | null;
}

export interface IngestResult {
  status: string;
  document_id: number;
  file_name: string;
  chunks_created: number;
  message?: string;
}

// ─── Document management ─────────────────────────────────────────────────────

export async function listDocuments(): Promise<RagDocument[]> {
  const res = await fetch(`${API_BASE}/api/rag/documents`);
  if (!res.ok) throw new Error(`Failed to list documents: HTTP ${res.status}`);
  return res.json();
}

export async function ingestDocument(file: File): Promise<IngestResult> {
  const form = new FormData();
  form.append('file', file);

  const res = await fetch(`${API_BASE}/api/rag/ingest`, {
    method: 'POST',
    body: form,
    // Do NOT set Content-Type — the browser sets it with the multipart boundary
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function deleteDocument(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/rag/documents/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }
}

// ─── RAG query stream ─────────────────────────────────────────────────────────

export interface RagQueryOptions {
  topK?: number;
  minSimilarity?: number;
}

/**
 * Stream a RAG query. Yields text tokens as they arrive.
 * The generator's return value contains the source file list extracted from
 * the penultimate SSE event.
 *
 * Usage:
 *   const gen = streamRagQuery(question);
 *   for await (const token of gen) { ... }
 *   const { sources } = await gen.return(undefined);   // not quite — see hook
 *
 * In practice the hook uses the onSources callback pattern below to receive
 * sources without needing the generator's return value.
 */
export async function* streamRagQuery(
  question: string,
  onSources: (sources: string[]) => void,
  options: RagQueryOptions = {},
): AsyncGenerator<string> {
  const res = await fetch(`${API_BASE}/api/rag/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      top_k: options.topK ?? 5,
      min_similarity: options.minSimilarity ?? 0.3,
    }),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new Error(detail);
  }

  if (!res.body) throw new Error('No response body from server.');

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;

      const payload = line.slice('data:'.length).trim();
      if (payload === '[DONE]') return;

      try {
        const parsed: unknown = JSON.parse(payload);

        // Sources event — {"type":"sources","sources":[...]}
        if (
          typeof parsed === 'object' &&
          parsed !== null &&
          'type' in parsed &&
          (parsed as Record<string, unknown>)['type'] === 'sources'
        ) {
          const sourcesRaw = (parsed as Record<string, unknown>)['sources'];
          if (Array.isArray(sourcesRaw)) {
            onSources(sourcesRaw as string[]);
          }
          continue;
        }

        // Plain text token
        if (typeof parsed === 'string') {
          yield parsed;
        }
      } catch {
        // Malformed SSE line — skip
      }
    }
  }
}
