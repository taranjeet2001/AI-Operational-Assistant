from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.ticket_draft_service import TicketDraftService
from app.services.ticket_service import TicketService


class TicketUpdateInput(BaseModel):
    ticket_number: str = Field(description="Ticket ID to update, such as IT-0001 or IT-0002.")
    status: Literal["open", "in_progress", "resolved", "closed"] = Field(
        default="closed", description="New status for the ticket."
    )
    notes: str | None = Field(default=None, description="Optional explanation or reason for the status update.")


def build_ticket_update_tool(
    ticket_service: TicketService, ticket_drafts: TicketDraftService, conversation_id: str
) -> StructuredTool:
    def update_ticket(
        ticket_number: str,
        status: Literal["open", "in_progress", "resolved", "closed"] = "closed",
        notes: str | None = None,
    ) -> dict:
        """Update an existing support ticket's status to closed, resolved, or in_progress."""
        ticket = ticket_service.update_status(ticket_number, status, notes)
        if not ticket:
            return {"updated": False, "reason": f"Ticket {ticket_number.upper().strip()} was not found."}
        ticket_drafts.clear(conversation_id)
        return {
            "updated": True,
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
            "title": ticket.title,
        }

    return StructuredTool.from_function(
        func=update_ticket,
        name="ticket_update",
        description="Update or close an existing support ticket. Use this when the employee asks to close, resolve, or change the status of an existing ticket.",
        args_schema=TicketUpdateInput,
    )
