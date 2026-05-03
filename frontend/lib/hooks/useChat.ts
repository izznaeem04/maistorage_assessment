"use client";

import { useState, useCallback, useRef } from "react";
import type { Message } from "@/types";
import { fetchMessages, streamChat } from "@/lib/api";

export function useChat(sessionId: string | null) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  // Accumulate streamed tokens without stale closure issues
  const streamBufferRef = useRef("");

  const loadMessages = useCallback(async () => {
    if (!sessionId) {
      setMessages([]);
      return;
    }
    try {
      const data = await fetchMessages(sessionId);
      setMessages(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages");
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (content: string, overrideSessionId?: string) => {
      const id = overrideSessionId ?? sessionId;
      if (!id || isStreaming) return;

      // Optimistically add the user message
      const tempUserMessage: Message = {
        id: `temp-${Date.now()}`,
        session_id: id,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, tempUserMessage]);
      streamBufferRef.current = "";
      setStreamingContent("");
      setIsStreaming(true);
      setError(null);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await streamChat(
          id,
          content,
          {
            onToken: (token) => {
              streamBufferRef.current += token;
              setStreamingContent((prev) => prev + token);
            },
            onDone: (_messageId, _usage) => {
              // Replace optimistic state with persisted data from the server
              fetchMessages(id)
                .then((data) => setMessages(data))
                .catch(() => {});
              streamBufferRef.current = "";
              setStreamingContent("");
              setIsStreaming(false);
            },
            onError: (errMsg) => {
              setError(errMsg);
              setIsStreaming(false);
              streamBufferRef.current = "";
              setStreamingContent("");
            },
          },
          controller.signal
        );
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError(err instanceof Error ? err.message : "Request failed");
        }
        setIsStreaming(false);
        streamBufferRef.current = "";
        setStreamingContent("");
      }
    },
    [sessionId, isStreaming]
  );

  const cancelStream = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    streamingContent,
    isStreaming,
    error,
    loadMessages,
    sendMessage,
    cancelStream,
  };
}
