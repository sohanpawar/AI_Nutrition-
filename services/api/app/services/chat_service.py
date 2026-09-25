"""Chat orchestration — full Milestone 1 pipeline including ScopeGuard."""

from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.core import llm as llm_client
from app.core import scope_guard
from app.core.prompts import get_system_prompt
from app.db import repository as repo
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.response import AssistantResponse, Claim, DeclineReason

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    def __init__(self, code: str, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def normalize_sources(payload: AssistantResponse) -> AssistantResponse:
    """Milestone 1 invariant: every claim.source must be null."""
    return payload.model_copy(
        update={
            "claims": [Claim(text=claim.text, source=None) for claim in payload.claims]
        }
    )


def _history_as_messages(db: Session, conversation_id: UUID) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for message in repo.list_messages(db, conversation_id):
        if message.role not in {"user", "assistant"}:
            continue
        history.append({"role": message.role, "content": message.content})
    return history


def _persist_turn(
    db: Session,
    *,
    conversation_id: UUID,
    user_text: str,
    payload: AssistantResponse,
) -> ChatResponse:
    message_id = uuid4()
    repo.add_user_message(db, conversation_id, user_text)
    repo.add_assistant_message(
        db,
        conversation_id=conversation_id,
        content=payload.answer,
        claims=payload.claims,
        declined=payload.declined,
        decline_reason=payload.decline_reason,
        message_id=message_id,
    )
    db.commit()
    return ChatResponse.from_assistant(
        conversation_id=conversation_id,
        message_id=message_id,
        payload=payload,
    )


def handle_chat(db: Session, request: ChatRequest) -> ChatResponse:
    """Run the chat pipeline and persist a successful turn.

    Pipeline (architecture §7.1):
      1–2. Validate + load/create conversation
      3. ScopeGuard.pre_check → refusal without LLM if blocked
      4. Build messages: system + history + new user
      5. LLM structured completion
      6. Validate (fail closed → 502)
      7. Force claim.source = null
      8. ScopeGuard.post_check → replace with refusal if leaked
      9. Persist user + assistant
      10. Return DTO

    Milestone 2: inject retrieved context into the message list before step 5.
    """
    if request.conversation_id is None:
        conversation = repo.create_conversation(db)
        db.flush()
    else:
        conversation = repo.get_conversation(db, request.conversation_id)
        if conversation is None:
            raise ChatServiceError(
                "conversation_not_found",
                "No conversation found for the given conversation_id.",
                status_code=404,
            )

    # Step 3 — scope pre-check (skip LLM on block).
    pre = scope_guard.pre_check(request.message)
    if pre.blocked and pre.reason is not None:
        refusal = scope_guard.refusal_payload(pre.reason)
        return _persist_turn(
            db,
            conversation_id=conversation.id,
            user_text=request.message,
            payload=refusal,
        )

    prior = _history_as_messages(db, conversation.id)

    # Milestone 2 hook: retrieved = retriever.search(request.message)
    # Milestone 2 hook: prior = inject_retrieved_context(prior, retrieved)

    llm_messages: list[dict[str, str]] = [
        {"role": "system", "content": get_system_prompt()},
        *prior,
        {"role": "user", "content": request.message},
    ]

    try:
        raw_payload = llm_client.complete_structured(llm_messages)
    except llm_client.SchemaParseError as exc:
        logger.warning("LLM schema failure; raw=%r", getattr(exc, "raw", None))
        raise ChatServiceError(
            "schema_validation_failed",
            "The model returned an invalid structured response.",
            status_code=502,
        ) from exc
    except llm_client.ProviderUnavailableError as exc:
        logger.warning("LLM provider unavailable: %s", exc)
        raise ChatServiceError(
            "provider_unavailable",
            "The language model provider is temporarily unavailable.",
            status_code=503,
        ) from exc

    try:
        validated = AssistantResponse.model_validate(raw_payload.model_dump())
    except Exception as exc:
        logger.warning("Post-LLM Pydantic validation failed: %s", exc)
        raise ChatServiceError(
            "schema_validation_failed",
            "The model returned an invalid structured response.",
            status_code=502,
        ) from exc

    normalized = normalize_sources(validated)

    # Step 8 — scope post-check (catch leaks).
    post = scope_guard.post_check(normalized)
    if post.blocked and post.reason is not None:
        reason: DeclineReason = post.reason
        normalized = scope_guard.refusal_payload(reason)

    return _persist_turn(
        db,
        conversation_id=conversation.id,
        user_text=request.message,
        payload=normalized,
    )
