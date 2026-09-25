"use client";

import { useEffect, useRef } from "react";
import { MessageBubble, type UiMessage } from "./MessageBubble";

type MessageListProps = {
  messages: UiMessage[];
  selectedMessageId: string | null;
  onSelectMessage: (id: string) => void;
};

export function MessageList({
  messages,
  selectedMessageId,
  onSelectMessage,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list message-list-empty">
        <p>
          Ask about food, nutrition, or food safety. Calorie targets, weight
          goals, and medical advice are out of scope.
        </p>
      </div>
    );
  }

  return (
    <div className="message-list" role="log" aria-live="polite">
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          message={message}
          selected={
            message.role === "assistant" && message.id === selectedMessageId
          }
          onSelect={() => onSelectMessage(message.id)}
        />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
