"""Simple LangGraph agent with configurable LLM provider and MCP server."""
import asyncio
import os
from typing import Any, cast

from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.agent_graph import compile_tool_bound_graph, configure_mcp_http_logging
from utils.config import build_llm, build_mcp_config
from utils.debug import render_content, debug_messages
from utils.prompts import load_prompts, resolve_prompts_file

configure_mcp_http_logging()


async def main():
    """Run the agent."""
    mcp_client = MultiServerMCPClient(build_mcp_config())
    tools = await mcp_client.get_tools()
    model = build_llm(tools)

    print(f"Using LLM_PROVIDER={os.environ.get('LLM_PROVIDER', 'anthropic')}")
    print(f"Using MCP_SERVER={os.environ.get('MCP_SERVER', 'arcade')}")
    print(f"Loaded {len(tools)} tools\n")

    app = compile_tool_bound_graph(model, tools)

    prompts_type = os.environ.get("PROMPTS_TYPE", "simple")
    prompts_file = resolve_prompts_file(prompts_type)
    print(f"Using PROMPTS_TYPE={prompts_type} ({prompts_file})\n")

    for item_type, content in load_prompts(prompts_file):
        if item_type == "header":
            print("\n===============================\n")
            print(f"Currently Testing - {content}\n")
            continue
        if item_type != "prompt":
            continue
        assert isinstance(content, str)

        try:
            state = cast(Any, {"messages": [HumanMessage(content=content)]})
            result = await app.ainvoke(state)
            print("\n...............................\n")
            print("HUMAN:\n", content[:120], "..." if len(content) > 120 else "")
            debug_messages(result["messages"])
            print("FINAL ANSWER:\n")
            print(render_content(result["messages"][-1]))
            print()
        except Exception as e:  # pylint: disable=broad-exception-caught
            print(f"\n[ERROR] Scenario failed: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
