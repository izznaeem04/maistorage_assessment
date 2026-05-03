"use client";

import { useState, useEffect } from "react";
import type { Session } from "@/types";
import SessionSidebar from "@/components/SessionSidebar";
import ChatWindow from "@/components/ChatWindow";
import ChatInput from "@/components/ChatInput";
import { useChat } from "@/lib/hooks/useChat";
import { fetchSessions, createSession, deleteSession } from "@/lib/api";

export default function ChatApp() {
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);

  const {
    messages,
    streamingContent,
    isStreaming,
    error,
    loadMessages,
    sendMessage,
    cancelStream,
  } = useChat(activeSession?.id ?? null);

  useEffect(() => {
    fetchSessions().then(setSessions).catch(() => {});
  }, []);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  const handleSelectSession = (session: Session) => {
    setActiveSession(session);
  };

  const handleDeleteSession = async (sessionId: string) => {
    try {
      await deleteSession(sessionId);
    } catch {
      // ignore
    }
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (activeSession?.id === sessionId) setActiveSession(null);
  };

  const handleNewChat = () => setActiveSession(null);

  const handleSend = async (content: string) => {
    if (activeSession) {
      sendMessage(content);
      return;
    }
    // No active session — create one named after the first message
    const name =
      content.slice(0, 50).trim() + (content.length > 50 ? "..." : "");
    try {
      const newSession = await createSession(name);
      setActiveSession(newSession);
      setSessions((prev) => [newSession, ...prev]);
      sendMessage(content, newSession.id);
    } catch {
      // creation failed — sendMessage will be a no-op (no session id)
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 text-slate-800">
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSession?.id ?? null}
        onSelect={handleSelectSession}
        onDelete={handleDeleteSession}
        onNewChat={handleNewChat}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        {activeSession ? (
          <>
            <header className="flex items-center border-b border-slate-200 bg-white px-6 py-3">
              <h2 className="text-sm font-medium text-slate-700">
                {activeSession.name}
              </h2>
            </header>

            <ChatWindow
              messages={messages}
              streamingContent={streamingContent}
              isStreaming={isStreaming}
              error={error}
            />

            <ChatInput
              onSend={handleSend}
              disabled={isStreaming}
              onCancel={cancelStream}
              isStreaming={isStreaming}
            />
          </>
        ) : (
          <div className="flex flex-1 flex-col overflow-hidden">
            <ChatWindow
              messages={[]}
              streamingContent=""
              isStreaming={false}
              error={null}
            />
            <ChatInput
              onSend={handleSend}
              disabled={false}
              isStreaming={false}
            />
          </div>
        )}
      </div>
    </div>
  );
}
