/**
 * Shared API types — mirrors `services/api/app/schemas`.
 * Milestone 1: every Claim.source is null.
 */

export type DeclineReason =
  | "calorie_or_weight_target"
  | "medical_advice"
  | "out_of_scope";

export type Claim = {
  text: string;
  source: string | null;
};

/** Structured assistant payload (without transport IDs). */
export type AssistantResponse = {
  answer: string;
  claims: Claim[];
  declined: boolean;
  decline_reason: DeclineReason | null;
};

export type ChatRequest = {
  conversation_id: string | null;
  message: string;
};

export type ChatResponse = {
  conversation_id: string;
  message_id: string;
  role: "assistant";
  answer: string;
  claims: Claim[];
  declined: boolean;
  decline_reason: DeclineReason | null;
};

export type HistoryMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  claims: Claim[] | null;
  declined: boolean;
  decline_reason: DeclineReason | null;
  created_at: string;
};

export type ConversationHistory = {
  conversation_id: string;
  messages: HistoryMessage[];
};

export type ErrorBody = {
  code: string;
  message: string;
};

export type ErrorResponse = {
  error: ErrorBody;
};

/** Known error codes (see API ErrorResponse docs). */
export type ApiErrorCode =
  | "empty_message"
  | "validation_error"
  | "message_too_long"
  | "schema_validation_failed"
  | "provider_unavailable"
  | "conversation_not_found";
