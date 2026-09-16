import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from app.agent.support_agent_graph import SupportAgentGraphFactory
from app.database.models import MessageRole
from app.knowledge.knowledge_retriever import KnowledgeRetriever
from app.services.conversation_memory_service import ConversationMemoryService
from app.services.conversation_service import ConversationService
from app.services.ticket_draft_service import TicketDraftService
from app.services.ticket_service import TicketService
from app.tools.knowledge_search_tool import build_knowledge_search_tool
from app.tools.ticket_creation_tool import build_ticket_creation_tool
from app.tools.ticket_draft_tool import build_ticket_draft_tool
from app.tools.ticket_lookup_tool import build_ticket_lookup_tool


logger = logging.getLogger("operations_assistant.agent")


class SupportAgentService:
    recent_message_limit = 8
    summary_refresh_interval = 4

    def __init__(self, session: Session, retriever: KnowledgeRetriever) -> None:
        self.conversations = ConversationService(session)
        self.memory = ConversationMemoryService(session)
        self.ticket_service = TicketService(session)
        self.ticket_drafts = TicketDraftService(session)
        self.retriever = retriever

    def reply(self, conversation_id: str, user_message: str) -> tuple[str, str | None]:
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            raise ValueError("Conversation was not found.")

        history = self._load_history(conversation_id)
        summary = self.memory.get_summary(conversation_id)
        graph = SupportAgentGraphFactory().build(self._build_tools(conversation_id, user_message))
        result = graph.invoke(
            {
                "messages": [*history, HumanMessage(content=user_message)],
                "conversation_summary": summary,
                "pending_ticket_draft": self._pending_draft_context(conversation_id),
            }
        )
        assistant_message = self._last_assistant_message(result["messages"])

        self.conversations.add_message(conversation_id, MessageRole.USER, user_message)
        self._persist_tool_messages(conversation_id, result["messages"][len(history) + 1 :])
        self.conversations.add_message(conversation_id, MessageRole.ASSISTANT, assistant_message.content)
        self._refresh_summary_if_needed(conversation_id)
        return assistant_message.content, self._ticket_number_from_messages(result["messages"])

    def _build_tools(self, conversation_id: str, user_message: str):
        if self.ticket_drafts.get_pending(conversation_id) and self._is_confirmation_message(user_message):
            return [build_ticket_creation_tool(self.ticket_service, self.ticket_drafts, conversation_id)]

        tools = [
            build_knowledge_search_tool(self.retriever),
            build_ticket_lookup_tool(self.ticket_service),
            build_ticket_draft_tool(self.ticket_drafts, conversation_id),
        ]
        if self.ticket_drafts.get_pending(conversation_id):
            tools.append(build_ticket_creation_tool(self.ticket_service, self.ticket_drafts, conversation_id))
        return tools

    @staticmethod
    def _is_confirmation_message(message: str) -> bool:
        normalized_message = message.lower().strip()
        confirmation_phrases = (
            "confirm",
            "confirmed",
            "yes create",
            "create it",
            "go ahead",
            "raise it",
            "submit it",
            "looks good",
        )
        return any(phrase in normalized_message for phrase in confirmation_phrases)

    def _load_history(self, conversation_id: str):
        messages = []
        for message in self.conversations.list_messages(conversation_id):
            if message.role == MessageRole.USER:
                messages.append(HumanMessage(content=message.content))
            elif message.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=message.content))
        return messages[-self.recent_message_limit :]

    def get_pending_ticket_draft(self, conversation_id: str) -> dict | None:
        draft = self.ticket_drafts.get_pending(conversation_id)
        if draft is None:
            return None
        return {
            "title": draft.title,
            "description": draft.description,
            "category": draft.category,
            "priority": draft.priority,
            "employee_id": draft.employee_id,
            "device_details": draft.device_details,
            "error_message": draft.error_message,
        }

    def _pending_draft_context(self, conversation_id: str) -> str:
        draft = self.get_pending_ticket_draft(conversation_id)
        return json.dumps(draft) if draft else "No pending ticket draft."

    def _refresh_summary_if_needed(self, conversation_id: str) -> None:
        messages = self.conversations.list_messages(conversation_id)
        if len(messages) >= self.recent_message_limit and len(messages) % self.summary_refresh_interval == 0:
            self.memory.refresh(conversation_id, self._load_history(conversation_id))

    def _persist_tool_messages(self, conversation_id: str, messages: list) -> None:
        for message in messages:
            if isinstance(message, ToolMessage):
                logger.info(
                    "tool.call | conversation_id=%s | tool=%s | output=%s",
                    conversation_id,
                    message.name,
                    message.content,
                )
                self.conversations.add_message(
                    conversation_id,
                    MessageRole.TOOL,
                    str(message.content),
                    tool_name=message.name,
                )

    @staticmethod
    def _last_assistant_message(messages: list) -> AIMessage:
        return next(message for message in reversed(messages) if isinstance(message, AIMessage) and not message.tool_calls)

    @staticmethod
    def _ticket_number_from_messages(messages: list) -> str | None:
        for message in reversed(messages):
            if isinstance(message, ToolMessage) and message.name == "ticket_creation":
                return json.loads(message.content).get("ticket_number")
        return None
