/**
 * Client helpers for the FastAPI backend.
 */

import type {
  ChatRequest,
  ChatResponse,
  ConversationHistory,
  ErrorResponse,
} from "./types";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
