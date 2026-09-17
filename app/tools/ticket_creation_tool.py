from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.ticket_draft_service import TicketDraftService
from app.services.ticket_service import TicketCreateCommand, TicketService


class TicketCreationInput(BaseModel):
    confirmation: bool = Field(default=True, description="Confirms creation of the pending ticket draft.")
    allow_duplicate: bool = Field(
        default=False,
        description="Set true only when the user explicitly asks to create a new ticket even after a duplicate warning.",
    )


def build_ticket_creation_tool(
    ticket_service: TicketService, ticket_drafts: TicketDraftService, conversation_id: str
) -> StructuredTool:
    def create_ticket(confirmation: bool = True, allow_duplicate: bool = False) -> dict:
        """Create the pending IT ticket draft after the user has explicitly confirmed it."""
        if not confirmation:
            return {"created": False, "reason": "User has not confirmed the ticket draft."}
        draft = ticket_drafts.get_pending(conversation_id)
        if draft is None:
            return {"created": False, "reason": "There is no pending ticket draft to confirm."}

        duplicate = ticket_service.find_duplicate_by_title(draft.title)
        if duplicate and not allow_duplicate:
            ticket, score = duplicate
            return {
                "created": False,
                "duplicate_found": True,
                "reason": "A similar open or in-progress ticket already exists.",
                "match_score": round(score, 2),
                "existing_ticket": {
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status,
                    "employee_id": ticket.employee_id,
                },
            }

        ticket = ticket_service.create(
            conversation_id,
            TicketCreateCommand(
                title=draft.title,
                description=draft.description,
                category=draft.category,
                priority=draft.priority,
                employee_id=draft.employee_id,
                device_details=draft.device_details,
                error_message=draft.error_message,
            ),
        )
        ticket_drafts.mark_confirmed(draft)
        return {
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "title": ticket.title,
            "employee_id": ticket.employee_id,
        }

    return StructuredTool.from_function(
        func=create_ticket,
        name="ticket_creation",
        description=(
            "Create the pending ticket draft only after the user explicitly confirms the exact "
            "ticket details. Never create a ticket before that confirmation."
        ),
        args_schema=TicketCreationInput,
    )
