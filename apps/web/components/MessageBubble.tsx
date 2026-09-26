import type { Claim } from "@/lib/types";
import { AlertIcon, SparkIcon, UserIcon } from "./Icons";

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
      <span className="bubble-meta">
        {isUser ? <UserIcon size={13} /> : <SparkIcon size={13} />}
        {isUser ? "You" : "Assistant"}
      </span>
      <p className="bubble-text">{message.content}</p>
      {claimTexts.length > 0 ? (
        <ul className="bubble-claims">
          {claimTexts.map((text, index) => (
            <li key={`${message.id}-claim-${index}`}>{text}</li>
          ))}
        </ul>
      ) : null}
      {message.declined ? (
        <span className="bubble-declined">
          <AlertIcon size={14} />
          Declined (out of scope)
        </span>
      ) : null}
    </button>
  );
}
