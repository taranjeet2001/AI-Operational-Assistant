from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.ticket_draft_service import TicketDraftService
from app.services.ticket_service import TicketCreateCommand, TicketService


class TicketCreationInput(BaseModel):
    confirmation: bool = Field(default=True, description="Confirms creation of the pending ticket draft.")


def build_ticket_creation_tool(
    ticket_service: TicketService, ticket_drafts: TicketDraftService, conversation_id: str
) -> StructuredTool:
    def create_ticket(confirmation: bool = True) -> dict:
        """Create the pending IT ticket draft after the user has explicitly confirmed it."""
        if not confirmation:
            return {"created": False, "reason": "User has not confirmed the ticket draft."}
        draft = ticket_drafts.get_pending(conversation_id)
        if draft is None:
            return {"created": False, "reason": "There is no pending ticket draft to confirm."}
        ticket = ticket_service.create(
            conversation_id,
            TicketCreateCommand(
                title=draft.title,
                description=draft.description,
                category=draft.category,
                priority=draft.priority,
                device_details=draft.device_details,
                error_message=draft.error_message,
            ),
        )
        ticket_drafts.mark_confirmed(draft)
        return {"ticket_number": ticket.ticket_number, "status": ticket.status, "title": ticket.title}

    return StructuredTool.from_function(
        func=create_ticket,
        name="ticket_creation",
        description=(
            "Create the pending ticket draft only after the user explicitly confirms the exact "
            "ticket details. Never create a ticket before that confirmation."
        ),
        args_schema=TicketCreationInput,
    )
