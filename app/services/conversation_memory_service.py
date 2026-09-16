from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database.models import ConversationMemory


MEMORY_PROMPT = """Maintain a concise factual memory for an internal IT support conversation.
Preserve the current issue, the user's requested action, known ticket details (title,
description, category, priority, device, error), completed troubleshooting, ticket IDs,
and missing information. Do not invent facts. Return only the updated memory, in concise
bullet points. The memory will be used by an agent to continue the same request."""


class ConversationMemoryService:
    """Keeps compact, durable context alongside the full conversation audit trail."""

    recent_message_limit = 8

    def __init__(self, session: Session, model: ChatOpenAI | None = None) -> None:
        self.session = session
        if model is None:
            settings = get_settings()
            model = ChatOpenAI(
                api_key=settings.openai_api_key,
                model=settings.openai_chat_model,
                temperature=0,
            )
        self.model = model

    def get_summary(self, conversation_id: str) -> str:
        memory = self.session.get(ConversationMemory, conversation_id)
        return memory.summary if memory else "No prior conversation context."

    def refresh(self, conversation_id: str, messages: list[BaseMessage]) -> None:
        memory = self.session.get(ConversationMemory, conversation_id)
        existing_summary = memory.summary if memory else "No prior conversation context."
        recent_history = "\n".join(
            f"{message.type.title()}: {message.content}"
            for message in messages[-self.recent_message_limit :]
        )
        response = self.model.invoke(
            f"{MEMORY_PROMPT}\n\nExisting memory:\n{existing_summary}\n\n"
            f"Recent conversation:\n{recent_history}"
        )

        if memory is None:
            memory = ConversationMemory(conversation_id=conversation_id, summary=str(response.content))
            self.session.add(memory)
        else:
            memory.summary = str(response.content)
        self.session.commit()
