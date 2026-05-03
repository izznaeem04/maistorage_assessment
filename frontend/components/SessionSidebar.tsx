"use client";

import type { Session } from "@/types";

interface Props {
  sessions: Session[];
  activeSessionId: string | null;
  onSelect: (session: Session) => void;
  onDelete: (sessionId: string) => void;
  onNewChat: () => void;
}

export default function SessionSidebar({
  sessions,
  activeSessionId,
  onSelect,
  onDelete,
  onNewChat,
}: Props) {
  const handleDelete = (
    e: React.MouseEvent,
    sessionId: string
  ) => {
    e.stopPropagation();
    onDelete(sessionId);
  };

  return (
    <aside className="w-64 flex-shrink-0 flex flex-col border-r border-slate-200 bg-white">
      <div className="px-4 py-4 border-b border-slate-100 flex items-center justify-between">
        <h1 className="text-sm font-semibold text-slate-700 tracking-wide uppercase">
          LLM Chat
        </h1>
        <button
          onClick={onNewChat}
          className="rounded px-2 py-1 text-xs text-slate-500 hover:bg-slate-100 hover:text-slate-800 transition-colors"
          title="New chat"
        >
          + New
        </button>
      </div>

      <ul className="flex-1 overflow-y-auto py-2">
        {sessions.length === 0 && (
          <li className="px-4 py-3 text-xs text-slate-400">No sessions yet.</li>
        )}
        {sessions.map((session) => (
          <li key={session.id}>
            <button
              onClick={() => onSelect(session)}
              className={`group w-full flex items-center justify-between px-4 py-2.5 text-left text-sm transition-colors ${
                activeSessionId === session.id
                  ? "bg-slate-100 text-slate-900 font-medium"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-800"
              }`}
            >
              <span className="truncate flex-1 mr-2">{session.name}</span>
              <span className="flex items-center gap-1">
                {session.message_count != null && (
                  <span className="text-xs text-slate-400">
                    {session.message_count}
                  </span>
                )}
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => handleDelete(e, session.id)}
                  onKeyDown={(e) =>
                    e.key === "Enter" && handleDelete(e as unknown as React.MouseEvent, session.id)
                  }
                  className="opacity-0 group-hover:opacity-100 rounded px-1 text-slate-400 hover:text-red-500 transition-opacity text-xs"
                  aria-label="Delete session"
                >
                  del
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
