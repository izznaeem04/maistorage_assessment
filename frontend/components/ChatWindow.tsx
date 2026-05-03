"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import type { Message } from "@/types";
import MessageBubble from "@/components/MessageBubble";

interface Props {
  messages: Message[];
  streamingContent: string;
  isStreaming: boolean;
  error: string | null;
}

export default function ChatWindow({
  messages,
  streamingContent,
  isStreaming,
  error,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex flex-1 items-center justify-center text-slate-400 text-sm select-none">
        Type a message to start a new chat.
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {isStreaming && streamingContent && (
        <div className="flex justify-start">
          <div className="max-w-[75%] rounded-lg px-4 py-3 text-sm leading-relaxed bg-white border border-slate-200 text-slate-800">
            <div className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeKatex]}
              >
                {streamingContent}
              </ReactMarkdown>
            </div>
            <span className="inline-block w-1.5 h-3.5 ml-0.5 align-text-bottom bg-slate-400 animate-pulse" />
          </div>
        </div>
      )}

      {error && (
        <div className="text-center text-xs text-red-500 py-2">
          {error}
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
