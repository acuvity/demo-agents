"""Simple LangGraph agent with configurable LLM provider and MCP server."""
import asyncio
import logging
import os
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)


def build_llm(tools):
    """Build the LLM based on LLM_PROVIDER env var (anthropic or openrouter)."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    if provider == "openrouter":
        from langchain_openrouter import ChatOpenRouter  # type: ignore[import]
        model_name = os.environ.get("OPENROUTER_MODEL", "qwen3.6-plus-preview")
        return ChatOpenRouter(
            model=model_name,
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=0,
        ).bind_tools(tools)
    model_name = os.environ.get("LLM_MODEL", "claude-opus-4-6")
    return ChatAnthropic(model_name=model_name).bind_tools(tools)  # type: ignore[call-arg]


def build_mcp_config() -> dict:
    """Build the MCP client config based on MCP_SERVER env var (arcade or local)."""
    server = os.environ.get("MCP_SERVER", "arcade")
    if server == "local":
        return {"local": {
            "command": "uv",
            "args": ["run", "python3", "tools/local_tools.py"],
            "transport": "stdio",
        }}
    return {"arcade": {
        "url": os.environ["ARCADE_MCP_URL"],
        "transport": "streamable_http",
        "headers": {
            "Authorization": f"Bearer {os.environ['ARCADE_API_KEY']}",
            "Arcade-User-Id": os.environ["ARCADE_USER_ID"],
        },
    }}


async def main():
    """Run the agent."""
    mcp_client = MultiServerMCPClient(build_mcp_config())
    tools = await mcp_client.get_tools()
    model = build_llm(tools)

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
