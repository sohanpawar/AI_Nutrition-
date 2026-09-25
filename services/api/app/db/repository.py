from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Conversation, Message
from app.schemas.response import Claim


def create_conversation(db: Session) -> Conversation:
    conversation = Conversation(id=uuid4())
    db.add(conversation)
    db.flush()
    return conversation


def get_conversation(db: Session, conversation_id: UUID) -> Conversation | None:
    stmt = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    return db.scalars(stmt).first()


def add_user_message(db: Session, conversation_id: UUID, content: str) -> Message:
    message = Message(
        id=uuid4(),
        conversation_id=conversation_id,
        role="user",
        content=content,
        claims=None,
        declined=False,
        decline_reason=None,
    )
    db.add(message)
    _touch_conversation(db, conversation_id)
    db.flush()
    return message


def add_assistant_message(
    db: Session,
    *,
    conversation_id: UUID,
    content: str,
    claims: list[Claim],
    declined: bool = False,
    decline_reason: str | None = None,
    message_id: UUID | None = None,
) -> Message:
    message = Message(
        id=message_id or uuid4(),
        conversation_id=conversation_id,
        role="assistant",
        content=content,
        claims=[claim.model_dump() for claim in claims],
        declined=declined,
        decline_reason=decline_reason,
    )
    db.add(message)
    _touch_conversation(db, conversation_id)
    db.flush()
    return message


def list_messages(db: Session, conversation_id: UUID) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def _touch_conversation(db: Session, conversation_id: UUID) -> None:
    conversation = db.get(Conversation, conversation_id)
    if conversation is not None:
        conversation.updated_at = datetime.now(timezone.utc)
