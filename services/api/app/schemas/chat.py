"""Chat request/response DTOs and API error shapes."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.response import AssistantResponse, Claim, DeclineReason


# Soft schema bound; route also enforces MAX_MESSAGE_LENGTH (4000).
_MAX_MESSAGE_CHARS = 4000


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=_MAX_MESSAGE_CHARS)

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Message must not be empty or whitespace-only")
        return stripped


class ChatResponse(BaseModel):
    """Outbound chat DTO — AssistantResponse fields plus transport IDs."""

    conversation_id: UUID
    message_id: UUID
    role: Literal["assistant"] = "assistant"
    answer: str = Field(..., min_length=1)
    claims: list[Claim] = Field(default_factory=list)
    declined: bool = False
    decline_reason: DeclineReason | None = None

    @classmethod
    def from_assistant(
        cls,
        *,
        conversation_id: UUID,
        message_id: UUID,
        payload: AssistantResponse,
    ) -> "ChatResponse":
        # Fail closed: re-validate before returning to the client.
        validated = AssistantResponse.model_validate(payload.model_dump())
        return cls(
            conversation_id=conversation_id,
            message_id=message_id,
            answer=validated.answer,
            claims=validated.claims,
            declined=validated.declined,
            decline_reason=validated.decline_reason,
        )


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error envelope.

    HTTP mapping (Milestone 1):
    - 400 `empty_message` / validation errors — bad client input
    - 502 `schema_validation_failed` — model output failed schema (Phase 4+; do not ship prose)
    - 503 `provider_unavailable` — LLM timeout/quota (Phase 4+)
    - 404 `conversation_not_found` — unknown conversation_id (Phase 3+)
    """

    error: ErrorBody
