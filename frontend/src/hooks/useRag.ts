import { useState, useCallback, useRef, useEffect } from 'react';
import {
  streamRagQuery,
  ingestDocument,
  listDocuments,
  deleteDocument,
  type RagDocument,
  type RagQueryOptions,
} from '../services/ragApi';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface RagMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  /** Source files attached to an assistant message (populated after stream ends). */
  sources?: string[];
}

interface UseRagReturn {
  messages: RagMessage[];
  isLoading: boolean;
  error: string | null;
  documents: RagDocument[];
  isUploading: boolean;
  sendMessage: (question: string, options?: RagQueryOptions) => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  removeDocument: (id: number) => Promise<void>;
  clearError: () => void;
}

// ─── Hook ────────────────────────────────────────────────────────────────────

export function useRag(): UseRagReturn {
  const [messages, setMessages] = useState<RagMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<RagDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Stable ref keeps the async generator closure in sync with current messages
  const messagesRef = useRef<RagMessage[]>([]);

  // ── Document list ──────────────────────────────────────────────────────────

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load documents.';
      setError(msg);
    }
  }, []);

  useEffect(() => {
    void refreshDocuments();
  }, [refreshDocuments]);

  // ── Upload ─────────────────────────────────────────────────────────────────

  const uploadDocument = useCallback(
    async (file: File) => {
      setIsUploading(true);
      setError(null);
      try {
        await ingestDocument(file);
        await refreshDocuments();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Upload failed.';
        setError(msg);
      } finally {
        setIsUploading(false);
      }
    },
    [refreshDocuments],
  );

  // ── Delete ─────────────────────────────────────────────────────────────────

  const removeDocument = useCallback(
    async (id: number) => {
      setError(null);
      try {
        await deleteDocument(id);
        await refreshDocuments();
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Delete failed.';
        setError(msg);
      }
    },
    [refreshDocuments],
  );

  // ── Query ──────────────────────────────────────────────────────────────────

  const sendMessage = useCallback(
    async (question: string, options: RagQueryOptions = {}) => {
      const trimmed = question.trim();
      if (!trimmed || isLoading) return;

      setError(null);

      const userMsg: RagMessage = {
        id: crypto.randomUUID(),
        role: 'user',
        content: trimmed,
      };

      const assistantMsg: RagMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '',
        sources: [],
      };

      messagesRef.current = [...messagesRef.current, userMsg];
      setMessages([...messagesRef.current, assistantMsg]);
      setIsLoading(true);

      try {
        let accumulated = '';
        let resolvedSources: string[] = [];

        const onSources = (sources: string[]) => {
          resolvedSources = sources;
        };

        for await (const token of streamRagQuery(trimmed, onSources, options)) {
          accumulated += token;
          setMessages((prev) => {
            const next = [...prev];
            next[next.length - 1] = { ...assistantMsg, content: accumulated };
            return next;
          });
        }

        // Attach sources to the final assistant message
        const finalMsg: RagMessage = {
          ...assistantMsg,
          content: accumulated,
          sources: resolvedSources,
        };
        messagesRef.current = [...messagesRef.current, finalMsg];
        setMessages([...messagesRef.current]);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'An unknown error occurred.';
        setError(msg);
        // Remove empty placeholder on failure
        setMessages((prev) => prev.filter((m) => m.id !== assistantMsg.id));
        messagesRef.current = messagesRef.current.filter((m) => m.id !== userMsg.id);
      } finally {
        setIsLoading(false);
      }
    },
    [isLoading],
  );

  const clearError = useCallback(() => setError(null), []);

  return {
    messages,
    isLoading,
    error,
    documents,
    isUploading,
    sendMessage,
    uploadDocument,
    removeDocument,
    clearError,
  };
}
