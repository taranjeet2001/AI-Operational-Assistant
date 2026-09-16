from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.ticket_draft_service import TicketDraftCommand, TicketDraftService


class TicketDraftInput(BaseModel):
    title: str = Field(min_length=5, max_length=200, description="Short summary of the issue.")
    description: str = Field(min_length=10, description="Clear description of the user's problem.")
    category: str = Field(default="other", description="Issue category, such as vpn, access, email, or hardware.")
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    device_details: str | None = Field(default=None, description="Affected device, if known.")
    error_message: str | None = Field(default=None, description="Exact error, if known.")


def build_ticket_draft_tool(ticket_drafts: TicketDraftService, conversation_id: str) -> StructuredTool:
    def prepare_ticket_draft(
        title: str,
        description: str,
        category: str = "other",
        priority: Literal["low", "medium", "high", "critical"] = "medium",
        device_details: str | None = None,
        error_message: str | None = None,
    ) -> dict:
        """Prepare a ticket proposal for the user to review before creation."""
        draft = ticket_drafts.save(
            conversation_id,
            TicketDraftCommand(
                title=title,
                description=description,
                category=category,
                priority=priority,
                device_details=device_details,
                error_message=error_message,
            ),
        )
        return {
            "title": draft.title,
            "description": draft.description,
            "category": draft.category,
            "priority": draft.priority,
            "device_details": draft.device_details,
            "error_message": draft.error_message,
            "status": draft.status,
        }

    return StructuredTool.from_function(
        func=prepare_ticket_draft,
        name="ticket_draft",
        description=(
            "Prepare or update a ticket draft when a user wants a ticket. This does not create a "
            "ticket. Use it before asking the user to review and confirm the exact details."
        ),
        args_schema=TicketDraftInput,
    )
