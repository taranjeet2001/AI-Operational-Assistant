from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class SupportAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    conversation_summary: str
    pending_ticket_draft: str
