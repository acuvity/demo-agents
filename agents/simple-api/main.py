"""Simple LangGraph agent using Arcade MCP tools."""
import argparse
import asyncio
import logging
import os
import secrets
from dataclasses import dataclass

import requests
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from opentelemetry import trace

from otel import setup_otel


@dataclass
class TurnConfig:
    """Per-turn request configuration."""
    auth_headers: dict
    source: dict
    verify_ssl: bool

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

tracer = trace.get_tracer(__name__)

APEX_URL = os.environ["APEX_URL"]
ARCADE_MCP_URL = os.environ.get("ARCADE_MCP_URL")
ARCADE_API_KEY = os.environ.get("ARCADE_API_KEY")
ARCADE_USER_ID = os.environ.get("ARCADE_USER_ID")
REQUEST_TIMEOUT = 30


def load_sections(path: str) -> dict[str, list[str]]:
    """Parse prompts.txt into {section_name: [prompts]} preserving order."""
    sections: dict[str, list[str]] = {}
    current = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#"):
                current = line.lstrip("#").strip()
                sections[current] = []
            elif line and current is not None:
                sections[current].append(line)
    return sections


async def run_turn(app, cfg: TurnConfig, conversation_id, prompt):
    """Run a single prompt through the agent and police API."""
    with tracer.start_as_current_span("turn:" + conversation_id) as turn_span:
        ctx = turn_span.get_span_context()
        traceparent = f"00-{ctx.trace_id:032x}-{ctx.span_id:016x}-01"
        trace_headers = {**cfg.auth_headers, "traceparent": traceparent}

        res = requests.post(
            f"{APEX_URL}/api/v1/police",
            json={
                "messages": [prompt],
                "source": cfg.source,
                "type": "Input",
                "provider": "anthropic-api",
                "conversationID": conversation_id,
            },
            verify=cfg.verify_ssl,
            headers=trace_headers,
            timeout=REQUEST_TIMEOUT,
        )
        print(res.json())

        result = await app.ainvoke(
            {"messages": [HumanMessage(content=prompt)]},
            {"configurable": {"thread_id": conversation_id}},
        )
        response_text = result["messages"][-1].content

        output = requests.post(
            f"{APEX_URL}/api/v1/police",
            json={
                "messages": [response_text],
                "source": cfg.source,
                "type": "Output",
                "provider": "anthropic-api",
                "conversationID": conversation_id,
            },
            verify=cfg.verify_ssl,
            headers=trace_headers,
            timeout=REQUEST_TIMEOUT,
        )
        print(output.json())
        print("Human: ", prompt)
        print(response_text + "\n")


async def build_app():
    """Build and return the compiled LangGraph app."""
    tools = []
    if ARCADE_MCP_URL and ARCADE_API_KEY and ARCADE_USER_ID:
        mcp_client = MultiServerMCPClient(
            {"arcade": {
                "url": ARCADE_MCP_URL,
                "transport": "streamable_http",
                "headers": {
                    "Authorization": f"Bearer {ARCADE_API_KEY}",
                    "Arcade-User-Id": ARCADE_USER_ID,
                },
            }}
        )
        tools = await mcp_client.get_tools()

    model = ChatAnthropic(model_name="claude-opus-4-6").bind_tools(tools)  # type: ignore[call-arg]

    def call_model(state: MessagesState):
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    if tools:
        graph.add_node("tools", ToolNode(tools))
        graph.add_edge(START, "call_model")
        graph.add_conditional_edges("call_model", tools_condition)
        graph.add_edge("tools", "call_model")
    else:
        graph.add_edge(START, "call_model")
    return graph.compile(checkpointer=InMemorySaver())


async def main():
    """Run the agent."""
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--conversation", metavar="NAME")
    group.add_argument("--multi-conversation", metavar="NAME")
    parser.add_argument("--trace", metavar="FILE", nargs="?", const="trace.jsonl")
    parser.add_argument("--secure", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    if args.trace:
        os.environ["OTEL_SPAN_FILE"] = args.trace
    setup_otel()

    app = await build_app()

    cfg = TurnConfig(
        auth_headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ['APP_COMP_TOKEN']}",
        },
        source={"username": "alice1234", "userClaims": ["email=alice@example.com"]},
        verify_ssl=args.secure,
    )
    sections = load_sections("./prompts.txt")

    if args.conversation:
        name = args.conversation
        prompts = sections.get(name)
        if not prompts:
            raise SystemExit(f"Section '{name}' not found in prompts.txt")
        print("===============================")
        print(f"Conversation: {name}\n")
        for prompt in prompts:
            await run_turn(app, cfg, secrets.token_hex(16), prompt)

    elif args.multi_conversation:
        name = args.multi_conversation
        prompts = sections.get(name)
        if not prompts:
            raise SystemExit(f"Section '{name}' not found in prompts.txt")
        print("===============================")
        print(f"Multi-turn conversation: {name}\n")
        conversation_id = secrets.token_hex(16)
        with tracer.start_as_current_span("conversation:" + conversation_id):
            for prompt in prompts:
                await run_turn(app, cfg, conversation_id, prompt)


asyncio.run(main())
