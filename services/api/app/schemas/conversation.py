"""Conversation history DTOs."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.response import Claim, DeclineReason


class HistoryMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    claims: list[Claim] | None = None
    declined: bool = False
    decline_reason: DeclineReason | None = None
    created_at: datetime


class ConversationHistory(BaseModel):
    conversation_id: UUID
    messages: list[HistoryMessage] = Field(default_factory=list)
