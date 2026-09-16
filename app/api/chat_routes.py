import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.support_agent_service import SupportAgentService
from app.api.schemas import (
    ChatMessageRequest,
    ChatMessageResponse,
    ConversationHistoryResponse,
    ConversationMessageResponse,
    ConversationResponse,
    ConversationSummaryResponse,
)
from app.database.database import get_session
from app.knowledge.knowledge_retriever import get_knowledge_retriever
from app.services.conversation_service import ConversationService
from app.services.ticket_draft_service import TicketDraftService

router = APIRouter(prefix="/conversations", tags=["conversations"])
logger = logging.getLogger("operations_assistant.chat")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(session: Session = Depends(get_session)) -> ConversationResponse:
    conversation = ConversationService(session).create()
    return ConversationResponse(conversation_id=conversation.id)


@router.get("", response_model=list[ConversationSummaryResponse])
def list_conversations(session: Session = Depends(get_session)) -> list[ConversationSummaryResponse]:
    conversations = ConversationService(session).list_conversations()
    return [
        ConversationSummaryResponse(
            conversation_id=conversation.conversation_id,
            title=conversation.title,
            last_message=conversation.last_message,
            message_count=conversation.message_count,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )
        for conversation in conversations
    ]


@router.get("/{conversation_id}", response_model=ConversationHistoryResponse)
def get_conversation(
    conversation_id: str, session: Session = Depends(get_session)
) -> ConversationHistoryResponse:
    conversations = ConversationService(session)
    if conversations.get(conversation_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation was not found.")
    messages = conversations.list_messages(conversation_id)
    ticket_drafts = TicketDraftService(session)
    draft = ticket_drafts.get_pending(conversation_id)
    return ConversationHistoryResponse(
        conversation_id=conversation_id,
        pending_ticket={
            "title": draft.title,
            "description": draft.description,
            "category": draft.category,
            "priority": draft.priority,
            "employee_id": draft.employee_id,
            "device_details": draft.device_details,
            "error_message": draft.error_message,
        }
        if draft
        else None,
        messages=[
            ConversationMessageResponse(
                role=message.role,
                content=message.content,
                tool_name=message.tool_name,
                created_at=message.created_at,
            )
            for message in messages
        ],
    )


@router.delete("/{conversation_id}")
def delete_conversation(conversation_id: str, session: Session = Depends(get_session)) -> dict[str, bool]:
    deleted = ConversationService(session).delete(conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation was not found.")
    logger.info("chat.delete | conversation_id=%s", conversation_id)
    return {"deleted": True}


@router.post("/{conversation_id}/messages", response_model=ChatMessageResponse)
def send_message(
    conversation_id: str,
    request: ChatMessageRequest,
    session: Session = Depends(get_session),
) -> ChatMessageResponse:
    agent = SupportAgentService(session, get_knowledge_retriever())
    logger.info("chat.input | conversation_id=%s | message=%s", conversation_id, request.message)
    try:
        response, ticket_number = agent.reply(conversation_id, request.message)
    except ValueError as error:
        logger.error("chat.error | conversation_id=%s | error=%s", conversation_id, error)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    pending_ticket = agent.get_pending_ticket_draft(conversation_id)
    logger.info("chat.output | conversation_id=%s | response=%s", conversation_id, response)
    return ChatMessageResponse(
        response=response,
        ticket_number=ticket_number,
        pending_ticket=pending_ticket,
        requires_confirmation=pending_ticket is not None,
        requires_input=ticket_number is None and response.endswith("?"),
    )
