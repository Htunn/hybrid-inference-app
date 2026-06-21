import { useEffect, useRef } from 'react';
import { useRag, type RagMessage } from '../hooks/useRag';
import { DocumentUpload } from '../components/DocumentUpload';
import { DocumentList } from '../components/DocumentList';
import { InputBar } from '../components/InputBar';
import { SourceBadges } from '../components/SourceBadges';

// ─── RAG Chat Thread ─────────────────────────────────────────────────────────

function RagChatThread({
  messages,
  isLoading,
}: {
  messages: RagMessage[];
  isLoading: boolean;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-slate-500 text-sm px-6 text-center">
        <p>
          Upload documents on the left, then ask questions grounded in that content.
          <br />
          Answers will cite the source files.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-slate-800 text-slate-100 rounded-bl-sm'
              }`}
          >
            {msg.content}
            {msg.role === 'assistant' && isLoading && msg.content === '' && (
              <span className="inline-block w-2 h-4 bg-slate-400 animate-pulse rounded-sm ml-0.5 align-middle" />
            )}
          </div>

          {/* Source badges appear below assistant messages once streaming is done */}
          {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
            <div className="mt-1 max-w-[85%] px-1">
              <SourceBadges sources={msg.sources} />
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────────

export function RagPage() {
  const {
    messages,
    isLoading,
    error,
    documents,
    isUploading,
    sendMessage,
    uploadDocument,
    removeDocument,
    clearError,
  } = useRag();

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* ── Left panel: document management ─────────────────────────────── */}
      <aside className="flex w-72 shrink-0 flex-col gap-4 border-r border-slate-700 overflow-y-auto px-4 py-4">
        <div>
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
            Upload document
          </h2>
          <DocumentUpload onUpload={uploadDocument} isUploading={isUploading} />
        </div>

        <div className="flex flex-col gap-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Knowledge base
            {documents.length > 0 && (
              <span className="ml-1.5 rounded-full bg-slate-700 px-1.5 py-0.5 text-slate-300">
                {documents.length}
              </span>
            )}
          </h2>
          <DocumentList documents={documents} onDelete={removeDocument} />
        </div>
      </aside>

      {/* ── Right panel: RAG chat ──────────────────────────────────────── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Error banner */}
        {error && (
          <div
            role="alert"
            className="flex items-center justify-between gap-2 bg-red-900/60 px-4 py-2 text-xs text-red-200 shrink-0"
          >
            <span>{error}</span>
            <button
              onClick={clearError}
              aria-label="Dismiss error"
              className="text-red-300 hover:text-red-100 transition"
            >
              ✕
            </button>
          </div>
        )}

        <RagChatThread messages={messages} isLoading={isLoading} />
        <InputBar onSend={sendMessage} isLoading={isLoading} />
      </div>
    </div>
  );
}
