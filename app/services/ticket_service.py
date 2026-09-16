from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import SupportTicket


@dataclass(frozen=True)
class TicketCreateCommand:
    title: str
    description: str
    category: str = "other"
    priority: str = "medium"
    device_details: str | None = None
    error_message: str | None = None


class TicketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, conversation_id: str, command: TicketCreateCommand) -> SupportTicket:
        ticket = SupportTicket(
            ticket_number=None,
            conversation_id=conversation_id,
            title=command.title,
            description=command.description,
            category=command.category,
            priority=command.priority,
            device_details=command.device_details,
            error_message=command.error_message,
        )
        self.session.add(ticket)
        self.session.flush()
        ticket.ticket_number = f"IT-{ticket.id:04d}"
        self.session.commit()
        return ticket

    def find(self, ticket_number: str | None, search_text: str | None, status: str | None) -> list[SupportTicket]:
        statement = select(SupportTicket).order_by(SupportTicket.created_at.desc())
        if ticket_number:
            statement = statement.where(SupportTicket.ticket_number == ticket_number.upper())
        if status:
            statement = statement.where(SupportTicket.status == status)
        if search_text:
            pattern = f"%{search_text}%"
            statement = statement.where(
                SupportTicket.title.ilike(pattern) | SupportTicket.description.ilike(pattern)
            )
        return list(self.session.scalars(statement.limit(20)))
