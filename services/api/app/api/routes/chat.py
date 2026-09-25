"""Chat endpoint — thin HTTP layer over chat_service (Phase 4 LLM pipeline)."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.rate_limit import allow_request
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ErrorBody, ErrorResponse
from app.services import chat_service

router = APIRouter(prefix="/api", tags=["chat"])

MAX_MESSAGE_LENGTH = 4000


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Empty, too long, or invalid message",
        },
        status.HTTP_404_NOT_FOUND: {
            "model": ErrorResponse,
            "description": "Unknown conversation_id",
        },
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": ErrorResponse,
            "description": "Rate limit exceeded",
        },
        status.HTTP_502_BAD_GATEWAY: {
            "model": ErrorResponse,
            "description": (
                "Model output failed schema validation. "
                "Do not return unparsed prose. Error code: schema_validation_failed."
            ),
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ErrorResponse,
            "description": "LLM provider unavailable (timeout/quota/config)",
        },
    },
)
def chat(
    request: ChatRequest,
    http_request: Request,
    db: Session = Depends(get_db),
) -> ChatResponse:
    if len(request.message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorBody(
                code="message_too_long",
                message=f"Message must be at most {MAX_MESSAGE_LENGTH} characters.",
            ).model_dump(),
        )

    client_key = http_request.client.host if http_request.client else "unknown"
    if not allow_request(client_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=ErrorBody(
                code="rate_limited",
                message="Too many requests. Please wait and try again.",
            ).model_dump(),
        )

    try:
        return chat_service.handle_chat(db, request)
    except chat_service.ChatServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=ErrorBody(code=exc.code, message=exc.message).model_dump(),
        ) from exc
