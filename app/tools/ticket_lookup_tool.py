from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.services.ticket_service import TicketService


class TicketLookupInput(BaseModel):
    ticket_number: str | None = Field(default=None, description="Ticket ID such as IT-0001.")
    search_text: str | None = Field(default=None, description="Words from the issue title or description.")
    status: str | None = Field(default=None, description="Optional ticket status filter.")
    employee_id: str | None = Field(default=None, description="Employee ID such as EMP1024.")


def build_ticket_lookup_tool(ticket_service: TicketService) -> StructuredTool:
    def lookup_tickets(
        ticket_number: str | None = None,
        search_text: str | None = None,
        status: str | None = None,
        employee_id: str | None = None,
    ) -> dict:
        """Look up existing IT support tickets by ID, status, or issue details."""
        tickets = ticket_service.find(ticket_number, search_text, status, employee_id)
        return {
            "tickets": [
                {
                    "ticket_number": ticket.ticket_number,
                    "title": ticket.title,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "employee_id": ticket.employee_id,
                }
                for ticket in tickets
            ]
        }

    return StructuredTool.from_function(
        func=lookup_tickets,
        name="ticket_lookup",
        description="Look up existing IT tickets when the user asks for ticket status or existing requests.",
        args_schema=TicketLookupInput,
    )
