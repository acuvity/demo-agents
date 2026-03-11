import logging
import os
import sys
from typing import Literal

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

class LanggraphRuntime:

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.app_name = cfg["app_name"]
        self.mcp_config = self.setup_mcp_toolsets()
        self.mcp_client = None
        self.tools = []
        self.agent = None
        self.llm_with_tools = None

    def setup_mcp_toolsets(self) -> dict:
        mcp_config = {}
        if not self.cfg.get("mcp_servers"):
            return mcp_config
        for server in self.cfg["mcp_servers"]:
            server_name = server.get("name", server["url"])
            if server["url"].rstrip("/").endswith("/sse"):
                mcp_config[server_name] = {
                    "transport": "sse",
                    "url": server["url"],
                }
            else:
                mcp_config[server_name] = {
                    "transport": "http",
                    "url": server["url"],
                }
        return mcp_config

    def should_continue(self, state: MessagesState) -> Literal["tool_node", "__end__"]:
        messages = state["messages"]
        last_message = messages[-1]
        if last_message.tool_calls:
            return "tool_node"
        return END

    def llm_call(self, state: MessagesState):
        messages = state["messages"]
        response = self.llm_with_tools.invoke(messages)
        return {"messages": [response]}

    async def send(self, input: str) -> str:
        if self.agent is None:
            if self.mcp_config:
                self.mcp_client = MultiServerMCPClient(self.mcp_config)
                self.tools = await self.mcp_client.get_tools()

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY environment variable is not set. "
                    "Create a .env file with ANTHROPIC_API_KEY=sk-ant-... or export it in your shell."
                )
            llm = ChatAnthropic(model="claude-sonnet-4-20250514", api_key=api_key)

            if self.tools:
                self.llm_with_tools = llm.bind_tools(self.tools)
            else:
                self.llm_with_tools = llm

            agent_builder = StateGraph(MessagesState)
            agent_builder.add_node("llm_call", self.llm_call)

            if self.tools:
                tool_node = ToolNode(tools=self.tools)
                agent_builder.add_node("tool_node", tool_node)

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

        messages = [HumanMessage(content=input)]
        result = await self.agent.ainvoke({"messages": messages})

        final_message = result["messages"][-1]
        return final_message.content
