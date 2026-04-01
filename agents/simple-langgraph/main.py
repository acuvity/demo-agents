"""Simple LangGraph agent with configurable LLM provider and MCP server."""
import asyncio
import logging
import os
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)


def build_llm(tools):
    """Build the LLM based on LLM_PROVIDER env var (anthropic or openrouter)."""
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    if provider == "openrouter":
        from langchain_openrouter import ChatOpenRouter  # type: ignore[import]

        model_name = os.environ.get(
            "OPENROUTER_MODEL",
            "qwen/qwen3.6-plus-preview:free",
        )
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
        return {
            "local": {
                "command": "uv",
                "args": ["run", "python3", "tools/local_tools.py"],
                "transport": "stdio",
            }
        }

    return {
        "arcade": {
            "url": os.environ["ARCADE_MCP_URL"],
            "transport": "streamable_http",
            "headers": {
                "Authorization": f"Bearer {os.environ['ARCADE_API_KEY']}",
                "Arcade-User-Id": os.environ["ARCADE_USER_ID"],
            },
        }
    }


def render_content(message: Any) -> str:
    """Render message content safely for printing."""
    content = getattr(message, "content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)

    return str(content)


def debug_messages(messages: list[Any]) -> None:
    """Print the message trace so tool calls and tool outputs are visible."""
    print("\n--- Debug Trace ---")
    for idx, msg in enumerate(messages):
        msg_type = msg.__class__.__name__
        print(f"[{idx}] {msg_type}")

        tool_calls = getattr(msg, "tool_calls", None)
        if tool_calls:
            print(f"  tool_calls: {tool_calls}")

        name = getattr(msg, "name", None)
        if name:
            print(f"  name: {name}")

        content = render_content(msg)
        if content:
            print(f"  content: {content}")
    print("--- End Debug Trace ---\n")


async def main():
    """Run the agent."""
    mcp_client = MultiServerMCPClient(build_mcp_config())
    tools = await mcp_client.get_tools()
    model = build_llm(tools)

    print(f"Using LLM_PROVIDER={os.environ.get('LLM_PROVIDER', 'anthropic')}")
    print(f"Using MCP_SERVER={os.environ.get('MCP_SERVER', 'arcade')}")
    print(f"Loaded {len(tools)} tools\n")

    from langchain_core.messages import SystemMessage

    def call_model(state: MessagesState):
        messages = state["messages"]

        # Add grounding instruction
        system_instruction = SystemMessage(
            content=(
                "You are an AI assistant that uses tools.\n\n"
                "CRITICAL RULE:\n"
                "- You MUST base your answer ONLY on tool output.\n"
                "- Do NOT invent, assume, or hallucinate information.\n"
            )
        )
        return {"messages": [model.invoke([system_instruction] + messages)]}

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
            print(f"Currently Testing - {prompt}\n")
            continue

        if not prompt:
            continue

        result = await app.ainvoke(
            {"messages": [HumanMessage(content=prompt)]}
        )
        print("...............................")
        print("Human:", prompt)
        debug_messages(result["messages"])
        print("Final answer:")
        print(render_content(result["messages"][-1]))
        print()


if __name__ == "__main__":
    asyncio.run(main())