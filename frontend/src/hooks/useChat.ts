import { useState, useCallback, useRef } from 'react';
import { streamChat, type Message } from '../services/api';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
  clearError: () => void;
}

export function useChat(): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Keep a stable ref to messages so the async stream closure sees latest state
  const messagesRef = useRef<ChatMessage[]>([]);

  const sendMessage = useCallback(async (content: string) => {
    const trimmed = content.trim();
    if (!trimmed || isLoading) return;

    setError(null);

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
    };

    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
    };

    const updatedMessages = [...messagesRef.current, userMsg];
    messagesRef.current = updatedMessages;
    setMessages([...updatedMessages, assistantMsg]);
    setIsLoading(true);

    // Build the API payload from conversation history
    const apiMessages: Message[] = updatedMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    try {
      let accumulated = '';
      for await (const token of streamChat(apiMessages)) {
        accumulated += token;
        // Update the last (assistant) message in-place as tokens arrive
        setMessages((prev) => {
          const next = [...prev];
          next[next.length - 1] = { ...assistantMsg, content: accumulated };
          return next;
        });
      }
      // Commit final assistant message to the stable ref
      const finalAssistant: ChatMessage = { ...assistantMsg, content: accumulated };
      messagesRef.current = [...updatedMessages, finalAssistant];
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(message);
      // Remove the empty assistant placeholder on error
      setMessages((prev) => prev.filter((m) => m.id !== assistantMsg.id));
      messagesRef.current = updatedMessages;
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  const clearError = useCallback(() => setError(null), []);

  return { messages, isLoading, error, sendMessage, clearError };
}
