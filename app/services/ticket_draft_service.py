from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database.models import TicketDraft


@dataclass(frozen=True)
class TicketDraftCommand:
    title: str
    description: str
    category: str = "other"
    priority: str = "medium"
    employee_id: str | None = None
    device_details: str | None = None
    error_message: str | None = None


class TicketDraftService:
    """Stores a proposed ticket until the employee explicitly confirms it."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def save(self, conversation_id: str, command: TicketDraftCommand) -> TicketDraft:
        draft = self.session.get(TicketDraft, conversation_id)
        if draft is None:
            draft = TicketDraft(conversation_id=conversation_id, **command.__dict__)
            self.session.add(draft)
        else:
            for field, value in command.__dict__.items():
                setattr(draft, field, value)
            draft.status = "pending"
        self.session.commit()
        return draft

    def get_pending(self, conversation_id: str) -> TicketDraft | None:
        draft = self.session.get(TicketDraft, conversation_id)
        return draft if draft and draft.status == "pending" else None

    def mark_confirmed(self, draft: TicketDraft) -> None:
        draft.status = "confirmed"
        self.session.commit()
