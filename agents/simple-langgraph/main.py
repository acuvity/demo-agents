"""Simple LangGraph agent with configurable LLM provider and MCP server."""
import asyncio
import logging
import os

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from utils.config import build_llm, build_mcp_config
from utils.debug import render_content, debug_messages
from utils.prompts import load_prompts, resolve_prompts_file

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

SYSTEM_PROMPT = (
    "You are an AI assistant that uses tools.\n\n"
    "CRITICAL RULE:\n"
    "- You MUST base your answer on tool output(s).\n"
    "- Your answer MUST be SOLELY based on the tool output(s).\n"
)


async def main():
    """Run the agent."""
    mcp_client = MultiServerMCPClient(build_mcp_config())
    tools = await mcp_client.get_tools()
    model = build_llm(tools)

    print(f"Using LLM_PROVIDER={os.environ.get('LLM_PROVIDER', 'anthropic')}")
    print(f"Using MCP_SERVER={os.environ.get('MCP_SERVER', 'arcade')}")
    print(f"Loaded {len(tools)} tools\n")

    def call_model(state: MessagesState):
        return {"messages": [model.invoke(
            [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        )]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", tools_condition)
    graph.add_edge("tools", "call_model")
    app = graph.compile()

    prompts_type = os.environ.get("PROMPTS_TYPE", "simple")
    prompts_file = resolve_prompts_file(prompts_type)
    print(f"Using PROMPTS_TYPE={prompts_type} ({prompts_file})\n")

    for item_type, content in load_prompts(prompts_file):
        if item_type == "header":
            print("\n===============================\n")
            print(f"Currently Testing - {content}\n")
            continue

        if item_type == "turns":
            messages = []
            for turn_idx, turn_content in enumerate(content):
                print(f"\n--- Turn {turn_idx + 1} of {len(content)} ---")
                print("HUMAN:\n", turn_content[:120], "..." if len(turn_content) > 120 else "")
                result = await app.ainvoke({
                    "messages": messages + [HumanMessage(content=turn_content)]
                })
                new_messages = result["messages"][len(messages):]
                messages = result["messages"]
                debug_messages(new_messages)
                print("FINAL ANSWER:\n")
                print(render_content(result["messages"][-1]))
                print()
            continue

        result = await app.ainvoke({"messages": [HumanMessage(content=content)]})
        print("\n...............................\n")
        print("HUMAN:\n", content[:120], "..." if len(content) > 120 else "")
        debug_messages(result["messages"])
        print("FINAL ANSWER:\n")
        print(render_content(result["messages"][-1]))
        print()


if __name__ == "__main__":
    asyncio.run(main())
