"use client";

import { FormEvent, KeyboardEvent, useState } from "react";
import { SendIcon } from "./Icons";

type ChatInputProps = {
  disabled?: boolean;
  onSend: (message: string) => void;
};

export function ChatInput({ disabled = false, onSend }: ChatInputProps) {
  const [value, setValue] = useState("");

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    submit();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  }

  return (
    <form className="chat-input" onSubmit={handleSubmit}>
      <label className="sr-only" htmlFor="chat-message">
        Message
      </label>
      <textarea
        id="chat-message"
        rows={2}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about protein, leftovers, or cooking methods…"
        disabled={disabled}
        maxLength={4000}
      />
      <button
        type="submit"
        className="send-button"
        disabled={disabled || !value.trim()}
        aria-label={disabled ? "Sending" : "Send message"}
      >
        <SendIcon size={17} />
        <span>{disabled ? "Sending…" : "Send"}</span>
      </button>
    </form>
  );
}
