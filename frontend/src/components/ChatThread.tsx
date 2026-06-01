import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../hooks/useChat';

interface ChatThreadProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

export function ChatThread({ messages, isLoading }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom whenever messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-slate-500 text-sm px-6 text-center">
        <p>Start a conversation. Messages are processed by your local Gemma model.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-4 py-4">
      {messages.map((msg) => (
        <div
          key={msg.id}
          className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
        >
          <div
            className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words ${msg.role === 'user'
                ? 'bg-indigo-600 text-white rounded-br-sm'
                : 'bg-slate-800 text-slate-100 rounded-bl-sm'
              }`}
          >
            {msg.content}
            {/* Blinking cursor while streaming the assistant response */}
            {msg.role === 'assistant' && isLoading && msg.content === '' && (
              <span className="inline-block w-2 h-4 bg-slate-400 animate-pulse rounded-sm ml-0.5 align-middle" />
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
