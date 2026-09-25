/**
 * Client helpers for the FastAPI backend.
 *
 * In production we call same-origin `/api/*` (empty base URL). Next.js route
 * handlers proxy those to Railway via BACKEND_API_URL — avoids CORS and the
 * classic empty NEXT_PUBLIC_API_URL → Vercel 404 bug.
 */

import type {
  ChatRequest,
  ChatResponse,
  ConversationHistory,
  ErrorResponse,
} from "./types";

function clientApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (raw == null || raw.trim() === "") {
    return "";
  }
  return raw.trim().replace(/\/$/, "");
}

export const API_URL = clientApiBase();

async function readError(response: Response): Promise<string> {
  let message = `Request failed (${response.status})`;
  try {
    const err = (await response.json()) as ErrorResponse;
    if (err?.error?.message) {
      message = err.error.message;
    }
  } catch {
    // ignore JSON parse errors
  }
  return message;
}

export async function postChat(body: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.json() as Promise<ChatResponse>;
}

export async function getConversation(
  conversationId: string,
): Promise<ConversationHistory> {
  const response = await fetch(
    `${API_URL}/api/conversations/${conversationId}`,
  );

  if (!response.ok) {
    throw new Error(await readError(response));
  }

  return response.json() as Promise<ConversationHistory>;
}
