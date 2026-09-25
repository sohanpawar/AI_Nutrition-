import type { Claim } from "@/lib/types";

export type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  claims?: Claim[];
  declined?: boolean;
};

type MessageBubbleProps = {
  message: UiMessage;
  selected?: boolean;
  onSelect?: () => void;
};

export function MessageBubble({
  message,
  selected = false,
  onSelect,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const claimTexts =
    !isUser && message.claims?.length
      ? message.claims.map((c) => c.text)
      : [];

  return (
    <button
      type="button"
      className={`bubble ${isUser ? "bubble-user" : "bubble-assistant"}${selected ? " bubble-selected" : ""}`}
      onClick={isUser ? undefined : onSelect}
      disabled={isUser}
      aria-pressed={!isUser ? selected : undefined}
    >
      <span className="bubble-role">{isUser ? "You" : "Assistant"}</span>
      <p className="bubble-text">{message.content}</p>
      {claimTexts.length > 0 ? (
        <ul className="bubble-claims">
          {claimTexts.map((text, index) => (
            <li key={`${message.id}-claim-${index}`}>{text}</li>
          ))}
        </ul>
      ) : null}
      {message.declined ? (
        <span className="bubble-declined">Declined (out of scope)</span>
      ) : null}
    </button>
  );
}
