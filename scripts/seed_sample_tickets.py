from app.database.database import SessionLocal, create_database_tables
from app.database.models import MessageRole
from app.services.conversation_service import ConversationService
from app.services.ticket_service import TicketCreateCommand, TicketService


SAMPLE_TICKETS = [
    {
        "employee_id": "EMP1024",
        "user_message": "My VPN connection is stuck on connecting.",
        "assistant_message": "I found this existing VPN ticket for EMP1024: {ticket_number} is open.",
        "ticket": TicketCreateCommand(
            title="VPN connection stuck on connecting",
            description="Employee reports SecureConnect VPN remains stuck on Connecting when working remotely.",
            category="vpn",
            priority="high",
            employee_id="EMP1024",
            device_details="Windows 11 laptop",
            error_message="SecureConnect stuck on Connecting",
        ),
    },
    {
        "employee_id": "EMP2048",
        "user_message": "Outlook is not syncing emails on my laptop.",
        "assistant_message": "I found this existing Outlook ticket for EMP2048: {ticket_number} is open.",
        "ticket": TicketCreateCommand(
            title="Outlook desktop app not syncing emails",
            description="Employee reports Outlook desktop app is not receiving new emails, while web Outlook works.",
            category="email",
            priority="medium",
            employee_id="EMP2048",
            device_details="macOS 14 laptop",
            error_message="Outlook shows Trying to connect",
        ),
    },
]


def seed_sample_tickets() -> None:
    create_database_tables()
    session = SessionLocal()
    try:
        conversations = ConversationService(session)
        tickets = TicketService(session)

        for sample in SAMPLE_TICKETS:
            existing = tickets.find(
                ticket_number=None,
                search_text=sample["ticket"].title,
                status=None,
                employee_id=sample["employee_id"],
            )
            if existing:
                continue

            conversation = conversations.create()
            conversations.add_message(conversation.id, MessageRole.USER, sample["user_message"])
            ticket = tickets.create(conversation.id, sample["ticket"])
            conversations.add_message(
                conversation.id,
                MessageRole.ASSISTANT,
                sample["assistant_message"].format(ticket_number=ticket.ticket_number),
            )
            print(f"Seeded {ticket.ticket_number} for {sample['employee_id']}: {ticket.title}")
    finally:
        session.close()


if __name__ == "__main__":
    seed_sample_tickets()
