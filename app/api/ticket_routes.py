from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.schemas import TicketResponse
from app.database.database import get_session
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


def to_ticket_response(ticket) -> TicketResponse:
    return TicketResponse(
        ticket_number=ticket.ticket_number,
        title=ticket.title,
        description=ticket.description,
        category=ticket.category,
        priority=ticket.priority,
        status=ticket.status,
        device_details=ticket.device_details,
        error_message=ticket.error_message,
        created_at=ticket.created_at,
    )


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> list[TicketResponse]:
    tickets = TicketService(session).find(ticket_number=None, search_text=search, status=status_filter)
    return [to_ticket_response(ticket) for ticket in tickets]


@router.get("/{ticket_number}", response_model=TicketResponse)
def get_ticket(ticket_number: str, session: Session = Depends(get_session)) -> TicketResponse:
    tickets = TicketService(session).find(ticket_number=ticket_number, search_text=None, status=None)
    if not tickets:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket was not found.")
    return to_ticket_response(tickets[0])
