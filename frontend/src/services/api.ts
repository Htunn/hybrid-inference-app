/**
 * api.ts — Streaming chat service
 *
 * Opens a fetch stream to the backend proxy and yields tokens one-by-one
 * as they arrive via Server-Sent Events (SSE).
 *
 * Usage:
 *   for await (const token of streamChat(messages)) {
 *     appendToken(token);
 *   }
 */

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

export async function* streamChat(messages: Message[]): AsyncGenerator<string> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages }),
  });

  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore parse error — use status code message
    }
    throw new Error(detail);
  }

  if (!response.body) {
    throw new Error('No response body from server.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE messages are separated by double-newlines
    const parts = buffer.split('\n\n');
    // Keep the last (potentially incomplete) chunk in the buffer
    buffer = parts.pop() ?? '';

    for (const part of parts) {
      const line = part.trim();
      if (!line.startsWith('data:')) continue;
      const payload = line.slice('data:'.length).trim();
      if (payload === '[DONE]') return;
      try {
        const token: string = JSON.parse(payload);
        yield token;
      } catch {
        // Malformed SSE line — skip
      }
    }
  }
}
