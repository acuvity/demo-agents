"""Shared LangGraph agent wiring for batch CLI and FastAPI server."""
import logging

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition


SYSTEM_PROMPT = (
    "You are an AI assistant that uses tools.\n\n"
    "CRITICAL RULE:\n"
    "- You MUST base your answer on tool output(s).\n"
    "- Your answer MUST be SOLELY based on the tool output(s).\n"
)


def configure_mcp_http_logging() -> None:
    """Reduce noisy MCP streamable HTTP client logs."""
    logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)


def compile_tool_bound_graph(model, tools):
    """Build and compile the tool-calling MessagesState graph for the given model and tools."""

    def call_model(state: MessagesState):
        return {
            "messages": [
                model.invoke(
                    [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
                )
            ]
        }

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", tools_condition)
    graph.add_edge("tools", "call_model")
    return graph.compile()
