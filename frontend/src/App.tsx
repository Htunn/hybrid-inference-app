import { useState } from 'react';
import { useChat } from './hooks/useChat';
import { ChatThread } from './components/ChatThread';
import { InputBar } from './components/InputBar';
import { RagPage } from './pages/RagPage';

type Tab = 'chat' | 'rag';
type Provider = 'gemini' | 'ollama';

function App() {
  const [provider, setProvider] = useState<Provider>('gemini');
  const { messages, isLoading, error, sendMessage, clearError, clearMessages } = useChat();
  const [activeTab, setActiveTab] = useState<Tab>('chat');

  return (
    <div className="flex h-dvh flex-col bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-slate-700 px-4 py-3 shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white font-bold text-sm">
          AI
        </div>
        <div className="flex-1">
          <h1 className="text-sm font-semibold leading-none">Hybrid Inference Chat</h1>
          <p className="mt-0.5 text-xs text-slate-400">
            {provider === 'gemini' ? 'Cloud · Gemini 2.5 Flash' : 'Local · Gemma4 E4B via Ollama'}
          </p>
        </div>

        {/* Provider toggle */}
        <div className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5">
          <span className="text-xs text-slate-400">Provider:</span>
          <button
            type="button"
            onClick={() => setProvider(provider === 'gemini' ? 'ollama' : 'gemini')}
            className="flex items-center gap-1.5 rounded-md bg-slate-700 px-2.5 py-1 text-xs font-medium text-slate-200 transition hover:bg-slate-600"
          >
            <span className={`h-1.5 w-1.5 rounded-full ${provider === 'gemini' ? 'bg-blue-400' : 'bg-green-400'}`} />
            {provider === 'gemini' ? 'Gemini' : 'Ollama'}
            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </button>
        </div>

        {/* Clear chat button */}
        {activeTab === 'chat' && messages.length > 0 && (
          <button
            type="button"
            onClick={clearMessages}
            className="flex items-center gap-1.5 rounded-md bg-slate-800 px-2.5 py-1.5 text-xs font-medium text-slate-400 transition hover:bg-slate-700 hover:text-slate-200"
            title="Clear chat history"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
            Clear
          </button>
        )}

        {/* Tab switcher */}
        <nav className="flex rounded-lg bg-slate-800 p-0.5 gap-0.5" aria-label="Page tabs">
          <button
            type="button"
            onClick={() => setActiveTab('chat')}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${activeTab === 'chat'
              ? 'bg-indigo-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            Chat
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('rag')}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${activeTab === 'rag'
              ? 'bg-indigo-600 text-white shadow'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            RAG
          </button>
        </nav>
      </header>

      {activeTab === 'chat' ? (
        <>
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
          <InputBar onSend={(msg) => sendMessage(msg, provider)} isLoading={isLoading} />
        </>
      ) : (
        <RagPage />
      )}
    </div>
  );
}

export default App;
