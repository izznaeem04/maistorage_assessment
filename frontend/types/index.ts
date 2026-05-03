export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface Message {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  created_at: string;
}

export interface UsageMetadata {
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
}

export interface SSETokenEvent {
  token: string;
}

export interface SSEDoneEvent {
  message_id: string;
  usage?: UsageMetadata | null;
}

export interface SSEErrorEvent {
  error: string;
}
