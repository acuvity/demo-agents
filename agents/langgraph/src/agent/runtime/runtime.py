"""LangGraph agent runtime module."""
import logging
import os
import sys
from typing import Any, Literal, Mapping

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.sessions import (  # type: ignore[import-untyped]
    SSEConnection,
    StreamableHttpConnection,
)
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode
from mcp.shared.exceptions import McpError
import httpx

from config import AgentConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class LanggraphRuntime:
    """Runtime for the LangGraph agent."""

    # pylint: disable=too-many-instance-attributes
    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.app_name = cfg["app_name"]
        self.mcp_config: Mapping[str, SSEConnection | StreamableHttpConnection] = (
            self.setup_mcp_toolsets()
        )
        self.mcp_client: MultiServerMCPClient | None = None
        self.tools: list[Any] = []
        self.agent: Any = None
        self.llm_with_tools: Any = None
        self.tool_node: ToolNode | None = None

    def setup_mcp_toolsets(self) -> Mapping[str, SSEConnection | StreamableHttpConnection]:
        """Set up MCP toolset configuration from cfg."""
        mcp_config: dict[str, SSEConnection | StreamableHttpConnection] = {}
        mcp_servers = self.cfg.get("mcp_servers")
        if not mcp_servers:
            return mcp_config
        for server in mcp_servers:
            server_name = server.get("name", server["url"])
            if server["url"].rstrip("/").endswith("/sse"):
                mcp_config[server_name] = SSEConnection(transport="sse", url=server["url"])
            else:
                mcp_config[server_name] = StreamableHttpConnection(
                    transport="streamable_http", url=server["url"]
                )
        return mcp_config

    def should_continue(self, state: MessagesState) -> Literal["tool_node", "__end__"]:
        """Determine whether to call a tool or end the graph."""
        messages = state["messages"]
        last_message = messages[-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tool_node"
        return "__end__"

    def llm_call(self, state: MessagesState) -> dict[str, list[AnyMessage]]:
        """Invoke the LLM with the current message state."""
        messages = state["messages"]
        response: AnyMessage = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def _tool_error_messages(self, state: MessagesState, content: str) -> list[ToolMessage]:
        """Build ToolMessage errors for each tool call id from the last AI message."""
        messages = state.get("messages", [])
        last_message = messages[-1] if messages else None

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return [
                ToolMessage(content=content, tool_call_id=tool_call["id"], status="error")
                for tool_call in last_message.tool_calls
            ]

        return [ToolMessage(content=content, tool_call_id="unknown", status="error")]

    async def safe_tool_node(self, state: MessagesState) -> dict[str, list[ToolMessage]]:
        """Execute tool node with error handling for MCP and HTTP errors."""
        tool_node = self.tool_node
        if tool_node is None:
            return {"messages": []}
        try:
            return await tool_node.ainvoke(state)
        except McpError as e:
            return {"messages": self._tool_error_messages(state, str(e))}
        except httpx.HTTPStatusError as e:
            return {
                "messages": self._tool_error_messages(
                    state,
                    f"Tool call failed: {e.response.status_code} - {e.response.text}",
                )
            }
        except Exception as e:
            logger.exception("Unexpected error in tool node: %s", e)
            raise

    async def send(self, user_input: str) -> str:
        """Send a message to the agent and return the response."""
        if self.agent is None:
            if self.mcp_config:
                self.mcp_client = MultiServerMCPClient(dict(self.mcp_config))
                self.tools = await self.mcp_client.get_tools()

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Create a .env file with ANTHROPIC_API_KEY=sk-ant-... or export it"
                )
            llm = ChatAnthropic(  # type: ignore[call-arg]
                model_name="claude-sonnet-4-20250514", api_key=api_key
            )

            if self.tools:
                self.llm_with_tools = llm.bind_tools(self.tools)
            else:
                self.llm_with_tools = llm

            agent_builder = StateGraph(MessagesState)
            agent_builder.add_node("llm_call", self.llm_call)

            if self.tools:
                self.tool_node = ToolNode(tools=self.tools)
                agent_builder.add_node("tool_node", self.safe_tool_node)
            agent_builder.add_edge(START, "llm_call")

            if self.tools:
                agent_builder.add_conditional_edges(
                    "llm_call",
                    self.should_continue,
                    ["tool_node", END]
                )
                agent_builder.add_edge("tool_node", "llm_call")
            else:
                agent_builder.add_edge("llm_call", END)

            self.agent = agent_builder.compile()

        messages: list[AnyMessage] = [HumanMessage(content=user_input)]
        result = await self.agent.ainvoke(MessagesState(messages=messages))

        final_message = result["messages"][-1]
        return final_message.content
