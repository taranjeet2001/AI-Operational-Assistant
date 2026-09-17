from dataclasses import dataclass
from math import sqrt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import SupportTicket, TicketStatus
from app.knowledge.embedding_service import EmbeddingService


@dataclass(frozen=True)
class TicketCreateCommand:
    title: str
    description: str
    category: str = "other"
    priority: str = "medium"
    employee_id: str | None = None
    device_details: str | None = None
    error_message: str | None = None


class TicketService:
    duplicate_title_threshold = 0.60

    def __init__(self, session: Session) -> None:
        self.session = session

    def find_duplicate_by_title(self, title: str) -> tuple[SupportTicket, float] | None:
        statement = select(SupportTicket).where(
            SupportTicket.status.in_([TicketStatus.OPEN, TicketStatus.IN_PROGRESS])
        )
        tickets = list(self.session.scalars(statement))
        if not tickets:
            return None

        embeddings = EmbeddingService().embeddings
        new_title_embedding = embeddings.embed_query(title)
        best_ticket = None
        best_score = 0.0

        for ticket in tickets:
            score = self._cosine_similarity(new_title_embedding, embeddings.embed_query(ticket.title))
            if score > best_score:
                best_ticket = ticket
                best_score = score

        if best_ticket and best_score >= self.duplicate_title_threshold:
            return best_ticket, best_score
        return None

    def create(self, conversation_id: str, command: TicketCreateCommand) -> SupportTicket:
        ticket = SupportTicket(
            ticket_number=None,
            conversation_id=conversation_id,
            title=command.title,
            description=command.description,
            category=command.category,
            priority=command.priority,
            employee_id=command.employee_id,
            device_details=command.device_details,
            error_message=command.error_message,
        )
        self.session.add(ticket)
        self.session.flush()
        ticket.ticket_number = f"IT-{ticket.id:04d}"
        self.session.commit()
        return ticket

    def find(
        self,
        ticket_number: str | None,
        search_text: str | None,
        status: str | None,
        employee_id: str | None = None,
    ) -> list[SupportTicket]:
        statement = select(SupportTicket).order_by(SupportTicket.created_at.desc())
        if ticket_number:
            statement = statement.where(SupportTicket.ticket_number == ticket_number.upper())
        if status:
            statement = statement.where(SupportTicket.status == status)
        if employee_id:
            statement = statement.where(SupportTicket.employee_id == employee_id.upper())
        if search_text:
            pattern = f"%{search_text}%"
            statement = statement.where(
                SupportTicket.title.ilike(pattern) | SupportTicket.description.ilike(pattern)
            )
        return list(self.session.scalars(statement.limit(20)))

    @staticmethod
    def _cosine_similarity(first: list[float], second: list[float]) -> float:
        dot_product = sum(a * b for a, b in zip(first, second, strict=True))
        first_length = sqrt(sum(value * value for value in first))
        second_length = sqrt(sum(value * value for value in second))
        return dot_product / (first_length * second_length)
