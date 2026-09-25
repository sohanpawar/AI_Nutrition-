"""Conversation history endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import repository as repo
from app.db.session import get_db
from app.schemas.chat import ErrorBody, ErrorResponse
from app.schemas.conversation import ConversationHistory, HistoryMessage
from app.schemas.response import Claim, DeclineReason

router = APIRouter(prefix="/api", tags=["conversations"])


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationHistory,
    responses={
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Unknown conversation_id",
        },
    },
)
def get_conversation(
    conversation_id: UUID, db: Session = Depends(get_db)
) -> ConversationHistory:
    conversation = repo.get_conversation(db, conversation_id)
    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorBody(
                code="conversation_not_found",
                message="No conversation found for the given conversation_id.",
            ).model_dump(),
        )

    history: list[HistoryMessage] = []
    for message in conversation.messages:
        claims = None
        if message.claims is not None:
            claims = [Claim.model_validate(item) for item in message.claims]
        decline_reason: DeclineReason | None = None
        if message.decline_reason is not None:
            decline_reason = message.decline_reason  # type: ignore[assignment]
        history.append(
            HistoryMessage(
                id=message.id,
                role=message.role,  # type: ignore[arg-type]
                content=message.content,
                claims=claims,
                declined=message.declined,
                decline_reason=decline_reason,
                created_at=message.created_at,
            )
        )

    return ConversationHistory(conversation_id=conversation.id, messages=history)
