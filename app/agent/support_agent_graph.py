import json
import logging

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.agent.support_agent_prompt import SUPPORT_AGENT_PROMPT
from app.agent.support_agent_state import SupportAgentState
from app.config import get_settings


logger = logging.getLogger("operations_assistant.graph")


class SupportAgentGraphFactory:
    """Builds a small tool-calling graph for one conversation request."""

    def build(self, tools: list[BaseTool]):
        settings = get_settings()
        model = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=settings.openai_chat_model,
            temperature=0,
        )
        tool_enabled_model = model.bind_tools(tools)
        tool_node = ToolNode(tools)

        def call_model(state: SupportAgentState) -> dict:
            logger.info("graph.node | node=decision | state=%s", self._state_for_log(state))
            prompt = (
                f"{SUPPORT_AGENT_PROMPT}\n\n"
                f"Conversation summary:\n{state['conversation_summary']}\n\n"
                f"Pending ticket draft:\n{state['pending_ticket_draft']}"
            )
            system_message = SystemMessage(content=prompt)
            response = tool_enabled_model.invoke([system_message, *state["messages"]])
            logger.info(
                "graph.node.output | node=decision | tool_calls=%s | response=%s",
                self._tool_names(response),
                self._short_text(str(response.content)),
            )
            return {"messages": [response]}

        def run_tools(state: SupportAgentState) -> dict:
            requested_tools = self._tool_names(state["messages"][-1])
            logger.info(
                "graph.node | node=tools | requested_tools=%s | state=%s",
                requested_tools,
                self._state_for_log(state),
            )
            result = tool_node.invoke(state)
            logger.info(
                "graph.node.output | node=tools | tool_results=%s",
                self._tool_result_names(result.get("messages", [])),
            )
            return result

        def next_step(state: SupportAgentState) -> str:
            last_message = state["messages"][-1]
            next_node = "tools" if isinstance(last_message, AIMessage) and last_message.tool_calls else END
            logger.info(
                "graph.route | from=decision | to=%s | requested_tools=%s",
                next_node,
                self._tool_names(last_message),
            )
            return next_node

        graph = StateGraph(SupportAgentState)
        graph.add_node("decision", call_model)
        graph.add_node("tools", run_tools)
        graph.add_edge(START, "decision")
        graph.add_conditional_edges("decision", next_step, {"tools": "tools", END: END})
        graph.add_edge("tools", "decision")
        return graph.compile()

    @staticmethod
    def _state_for_log(state: SupportAgentState) -> str:
        payload = {
            "conversation_summary": state["conversation_summary"],
            "pending_ticket_draft": state["pending_ticket_draft"],
            "messages": [
                {
                    "type": message.type,
                    "content": SupportAgentGraphFactory._short_text(str(message.content)),
                    "tool_calls": SupportAgentGraphFactory._tool_names(message),
                }
                for message in state["messages"]
            ],
        }
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _tool_names(message: BaseMessage) -> list[str]:
        tool_calls = getattr(message, "tool_calls", None) or []
        return [tool_call.get("name", "unknown") for tool_call in tool_calls]

    @staticmethod
    def _tool_result_names(messages: list[BaseMessage]) -> list[str]:
        return [getattr(message, "name", "unknown") for message in messages]

    @staticmethod
    def _short_text(value: str, limit: int = 500) -> str:
        clean_value = " ".join(value.split())
        return clean_value if len(clean_value) <= limit else f"{clean_value[: limit - 1]}..."
