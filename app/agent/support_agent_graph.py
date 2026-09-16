from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.support_agent_prompt import SUPPORT_AGENT_PROMPT
from app.agent.support_agent_state import SupportAgentState
from app.config import get_settings


class SupportAgentGraphFactory:
    """Builds a small tool-calling graph for one conversation request."""

    def build(self, tools: list[BaseTool]):
        settings = get_settings()
        model = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model, temperature=0)
        tool_enabled_model = model.bind_tools(tools)

        def decide(state: SupportAgentState) -> dict:
            system_message = SystemMessage(
                content=(
                    f"{SUPPORT_AGENT_PROMPT}\n\nConversation summary:\n{state['conversation_summary']}"
                    f"\n\nPending ticket draft:\n{state['pending_ticket_draft']}"
                )
            )
            response = tool_enabled_model.invoke([system_message, *state["messages"]])
            return {"messages": [response]}

        def route_after_decision(state: SupportAgentState) -> str:
            last_message = state["messages"][-1]
            return "tools" if isinstance(last_message, AIMessage) and last_message.tool_calls else END

        graph = StateGraph(SupportAgentState)
        graph.add_node("decision", decide)
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "decision")
        graph.add_conditional_edges("decision", route_after_decision, {"tools": "tools", END: END})
        graph.add_edge("tools", "decision")
        return graph.compile()
