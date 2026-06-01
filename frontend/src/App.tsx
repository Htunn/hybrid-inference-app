import { useChat } from './hooks/useChat';
import { ChatThread } from './components/ChatThread';
import { InputBar } from './components/InputBar';

function App() {
  const { messages, isLoading, error, sendMessage, clearError } = useChat();

  return (
    <div className="flex h-dvh flex-col bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-slate-700 px-4 py-3 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-sm">
          AI
        </div>
        <div>
          <h1 className="text-sm font-semibold leading-none">Hybrid Inference Chat</h1>
          <p className="mt-0.5 text-xs text-slate-400">
            {import.meta.env.DEV ? 'Local · Gemma4 E4B via Ollama' : 'Cloud · Gemini 2.5 Flash'}
          </p>
        </div>
      </header>

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

      {/* Chat thread — scrollable */}
      <ChatThread messages={messages} isLoading={isLoading} />

      {/* Input */}
      <InputBar onSend={sendMessage} isLoading={isLoading} />
    </div>
  );
}

export default App;
