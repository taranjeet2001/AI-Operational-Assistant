from datetime import datetime

from pydantic import BaseModel, Field


class ConversationResponse(BaseModel):
    conversation_id: str


class ConversationMessageResponse(BaseModel):
    role: str
    content: str
    tool_name: str | None = None
    created_at: datetime


class ConversationSummaryResponse(BaseModel):
    conversation_id: str
    title: str
    last_message: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationHistoryResponse(BaseModel):
    conversation_id: str
    messages: list[ConversationMessageResponse]
    pending_ticket: dict | None = None


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10_000)


class ChatMessageResponse(BaseModel):
    response: str
    requires_input: bool
    requires_confirmation: bool = False
    ticket_number: str | None = None
    pending_ticket: dict | None = None


class TicketResponse(BaseModel):
    ticket_number: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    employee_id: str | None
    device_details: str | None
    error_message: str | None
    created_at: datetime


class KnowledgeSearchResponse(BaseModel):
    content: str
    source_file: str
    relevance_score: float
