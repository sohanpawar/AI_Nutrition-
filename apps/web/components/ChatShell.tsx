"use client";

import { useEffect, useMemo, useState } from "react";
import { getConversation, postChat } from "@/lib/api";
import type { Claim } from "@/lib/types";
import { ChatInput } from "./ChatInput";
import { AlertIcon, LeafIcon, PlusIcon } from "./Icons";
import { MessageList } from "./MessageList";
import type { UiMessage } from "./MessageBubble";
import { SourcesPanel } from "./SourcesPanel";

const STORAGE_KEY = "ai-nutrition.conversationId";

function newId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ChatShell() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(
    null,
  );
  const [sending, setSending] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      let stored: string | null = null;
      try {
        stored = window.localStorage.getItem(STORAGE_KEY);
      } catch {
        // localStorage may be unavailable
      }

      if (!stored) {
        if (!cancelled) setLoadingHistory(false);
        return;
      }

      try {
        const history = await getConversation(stored);
        if (cancelled) return;
        const loaded: UiMessage[] = history.messages.map((m) => ({
          id: m.id,
          role: m.role === "assistant" ? "assistant" : "user",
          content: m.content,
          claims: m.claims ?? undefined,
          declined: m.declined,
        }));
        setConversationId(history.conversation_id);
        setMessages(loaded);
        const lastAssistant = [...loaded]
          .reverse()
          .find((m) => m.role === "assistant");
        setSelectedMessageId(lastAssistant?.id ?? null);
      } catch {
        if (cancelled) return;
        try {
          window.localStorage.removeItem(STORAGE_KEY);
        } catch {
          // ignore
        }
        setConversationId(null);
        setMessages([]);
      } finally {
        if (!cancelled) setLoadingHistory(false);
      }
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (loadingHistory) return;
    try {
      if (conversationId) {
        window.localStorage.setItem(STORAGE_KEY, conversationId);
      }
    } catch {
      // ignore quota / privacy mode
    }
  }, [conversationId, loadingHistory]);

  const selectedClaims: Claim[] = useMemo(() => {
    const selected =
      messages.find((m) => m.id === selectedMessageId) ??
      [...messages].reverse().find((m) => m.role === "assistant");
    return selected?.claims ?? [];
  }, [messages, selectedMessageId]);

  async function handleSend(text: string) {
    setError(null);
    const userMessage: UiMessage = {
      id: newId(),
      role: "user",
      content: text,
    };
    setMessages((prev) => [...prev, userMessage]);
    setSending(true);

    try {
      const response = await postChat({
        conversation_id: conversationId,
        message: text,
      });

      setConversationId(response.conversation_id);

      const assistantMessage: UiMessage = {
        id: response.message_id,
        role: "assistant",
        content: response.answer,
        claims: response.claims,
        declined: response.declined,
      };

      setMessages((prev) => [...prev, assistantMessage]);
      setSelectedMessageId(assistantMessage.id);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";
      setError(message);
    } finally {
      setSending(false);
    }
  }

  function handleNewChat() {
    setConversationId(null);
    setMessages([]);
    setSelectedMessageId(null);
    setError(null);
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }

  return (
    <div className="chat-shell">
      <div className="ambient" aria-hidden="true">
        <span className="orb orb-a" />
        <span className="orb orb-b" />
        <span className="orb orb-c" />
      </div>
      <header className="chat-header">
        <div className="brand-lockup">
          <div className="brand-mark" aria-hidden="true">
            <LeafIcon size={22} />
          </div>
          <div>
            <p className="chat-eyebrow">AI Nutrition</p>
            <h1 className="chat-title">Assistant</h1>
            <p className="chat-tagline">
              Fresh answers on food, nutrients, and kitchen safety.
            </p>
          </div>
        </div>
        <button
          type="button"
          className="ghost-button"
          onClick={handleNewChat}
          disabled={sending || messages.length === 0}
        >
          <PlusIcon size={15} />
          New chat
        </button>
      </header>

      <div className="chat-body">
        <section className="chat-main panel-glass" aria-label="Conversation">
          {loadingHistory ? (
            <div className="message-list message-list-empty">
              <p>Loading conversation…</p>
            </div>
          ) : (
            <MessageList
              messages={messages}
              selectedMessageId={selectedMessageId}
              onSelectMessage={setSelectedMessageId}
              onSuggestionSend={handleSend}
              suggestionsDisabled={sending}
            />
          )}
          {error ? (
            <div className="chat-error" role="alert">
              <AlertIcon size={16} />
              <span>{error}</span>
            </div>
          ) : null}
          <ChatInput disabled={sending || loadingHistory} onSend={handleSend} />
        </section>

        <SourcesPanel claims={selectedClaims} />
      </div>
    </div>
  );
}
