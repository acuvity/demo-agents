"""Simple LangGraph agent using Arcade MCP tools."""
import asyncio
import logging
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from config import load_config_yaml
from observability import setup_otel

cfg = load_config_yaml()

setup_otel(cfg)

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

ARCADE_MCP_URL = os.environ["ARCADE_MCP_URL"]
ARCADE_API_KEY = os.environ["ARCADE_API_KEY"]
ARCADE_USER_ID = os.environ["ARCADE_USER_ID"]


async def main():
    """Run the agent."""
    mcp_client = MultiServerMCPClient(
        {"arcade": {
            "url": f"{ARCADE_MCP_URL}",
            "transport": "streamable_http",
            "headers": {
                "Authorization": f"Bearer {ARCADE_API_KEY}",
                "Arcade-User-Id": f"{ARCADE_USER_ID}",
            },
        }}
    )
    tools = await mcp_client.get_tools()
    model = ChatAnthropic(model_name="claude-opus-4-6").bind_tools(tools)  # type: ignore[call-arg]

    def call_model(state: MessagesState):
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", tools_condition)
    graph.add_edge("tools", "call_model")
    app = graph.compile()

    with open("./prompts.txt", "r", encoding="utf-8") as f:
        prompts = f.readlines()
        for prompt in prompts:
            prompt = prompt.strip()
            if prompt.startswith("#"):
                print("===============================")
                print(f"Currently Testing - {prompt}\n\n")
                continue
            if not prompt:
                continue
            result = await app.ainvoke(
                {"messages": [HumanMessage(content=prompt)]}
            )
            print("Human: ", prompt)
            print(result["messages"][-1].content+"\n")


asyncio.run(main())
