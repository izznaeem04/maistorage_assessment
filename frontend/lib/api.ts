import type { Session, Message } from "@/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---- Sessions ---------------------------------------------------------------

export async function fetchSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/sessions/`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function createSession(name: string): Promise<Session> {
  const res = await fetch(`${API_URL}/sessions/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to create session");
  }
  return res.json();
}

export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_URL}/sessions/${sessionId}`, {
    method: "DELETE",
  });
  if (!res.ok && res.status !== 204) {
    throw new Error("Failed to delete session");
  }
}

// ---- Messages ---------------------------------------------------------------

export async function fetchMessages(sessionId: string): Promise<Message[]> {
  const res = await fetch(
    `${API_URL}/chat/sessions/${sessionId}/messages`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

// ---- Streaming chat ---------------------------------------------------------

export interface StreamCallbacks {
  onToken: (token: string) => void;
  onDone: (messageId: string, usage: object | null) => void;
  onError: (error: string) => void;
}

export async function streamChat(
  sessionId: string,
  content: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, content }),
    signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }

  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const raw = line.slice(6).trim();
        if (!raw) continue;
        try {
          const payload = JSON.parse(raw);
          if (currentEvent === "token" && typeof payload.token === "string") {
            callbacks.onToken(payload.token);
          } else if (currentEvent === "done") {
            callbacks.onDone(payload.message_id, payload.usage ?? null);
          } else if (currentEvent === "error") {
            callbacks.onError(payload.error ?? "Unknown streaming error");
          }
        } catch {
          // malformed JSON — skip
        }
        currentEvent = "";
      }
    }
  }
}
