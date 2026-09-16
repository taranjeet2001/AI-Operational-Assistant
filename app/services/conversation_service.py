from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Conversation, ConversationMessage, MessageRole


@dataclass(frozen=True)
class ConversationSummary:
    conversation_id: str
    title: str
    last_message: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self) -> Conversation:
        conversation = Conversation()
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        return self.session.get(Conversation, conversation_id)

    def list_conversations(self) -> list[ConversationSummary]:
        statement = select(Conversation).order_by(Conversation.updated_at.desc(), Conversation.created_at.desc())
        conversations = list(
            self.session.scalars(statement)
        )
        return [self._build_summary(conversation) for conversation in conversations]

    def list_messages(self, conversation_id: str) -> list[ConversationMessage]:
        statement = (
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation_id)
            .order_by(ConversationMessage.created_at, ConversationMessage.id)
        )
        return list(self.session.scalars(statement))

    def add_message(
        self,
        conversation_id: str,
        role: MessageRole,
        content: str,
        tool_name: str | None = None,
        tool_payload: dict | None = None,
    ) -> ConversationMessage:
        message = ConversationMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_payload=tool_payload,
        )
        conversation = self.session.get(Conversation, conversation_id)
        if conversation:
            conversation.updated_at = datetime.now(UTC)
        self.session.add(message)
        self.session.commit()
        return message

    def _build_summary(self, conversation: Conversation) -> ConversationSummary:
        messages = self.list_messages(conversation.id)
        visible_messages = [
            message for message in messages if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        first_user_message = next((message for message in visible_messages if message.role == MessageRole.USER), None)
        last_visible_message = visible_messages[-1] if visible_messages else None
        title = self._shorten(first_user_message.content if first_user_message else "New conversation", 54)
        last_message = self._shorten(last_visible_message.content, 90) if last_visible_message else None
        return ConversationSummary(
            conversation_id=conversation.id,
            title=title,
            last_message=last_message,
            message_count=len(visible_messages),
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _shorten(value: str, max_length: int) -> str:
        clean_value = " ".join(value.split())
        return clean_value if len(clean_value) <= max_length else f"{clean_value[: max_length - 1]}..."
