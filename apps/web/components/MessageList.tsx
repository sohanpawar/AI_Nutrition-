"use client";

import { useEffect, useRef } from "react";
import { BowlIcon, LeafIcon, ShieldIcon } from "./Icons";
import { MessageBubble, type UiMessage } from "./MessageBubble";

type MessageListProps = {
  messages: UiMessage[];
  selectedMessageId: string | null;
  onSelectMessage: (id: string) => void;
  onSuggestionSend?: (message: string) => void;
  suggestionsDisabled?: boolean;
};

const SUGGESTIONS = [
  {
    icon: LeafIcon,
    text: "How much protein do vegetarians need?",
  },
  {
    icon: ShieldIcon,
    text: "How long can cooked chicken stay in the fridge?",
  },
  {
    icon: BowlIcon,
    text: "Does boiling vegetables destroy nutrients?",
  },
] as const;

export function MessageList({
  messages,
  selectedMessageId,
  onSelectMessage,
  onSuggestionSend,
  suggestionsDisabled = false,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="message-list message-list-empty">
        <div className="empty-hero">
          <div className="empty-icon">
            <LeafIcon size={26} />
          </div>
          <h2>Fuel your curiosity</h2>
          <p>
            Tap a colorful starter below, or type anything about nutrients,
            leftovers, or cooking methods.
          </p>
          {onSuggestionSend ? (
            <div className="suggestion-row">
              {SUGGESTIONS.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.text}
                    type="button"
                    className="suggestion-chip"
                    disabled={suggestionsDisabled}
                    onClick={() => onSuggestionSend(item.text)}
                  >
                    <Icon size={16} />
                    {item.text}
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>
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
