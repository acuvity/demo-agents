"""FastAPI entrypoint for the simple-langgraph demo agent."""
import asyncio
import logging
import os

from fastapi import FastAPI
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from utils.config import build_llm, build_mcp_config

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

SYSTEM_PROMPT = (
    "You are an AI assistant that uses tools.\n\n"
    "CRITICAL RULE:\n"
    "- You MUST base your answer on tool output(s).\n"
    "- Your answer MUST be SOLELY based on the tool output(s).\n"
)

app = FastAPI(title="Simple LangGraph Demo Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_agent = None
_lock = asyncio.Lock()


async def get_agent():
    """Lazily initialize and return the compiled LangGraph agent."""
    global _agent
    async with _lock:
        if _agent is None:
            mcp_client = MultiServerMCPClient(build_mcp_config())
            tools = await mcp_client.get_tools()
            model = build_llm(tools)

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
            _agent = graph.compile()
            logging.info("Agent initialized with %d tools", len(tools))
    return _agent


class MessageRequest(BaseModel):
    """Request body for the /send endpoint."""

    message: str


@app.post("/send")
async def send_message(req: MessageRequest):
    """Handle an incoming chat message and return the agent response."""
    agent = await get_agent()
    result = await agent.ainvoke({"messages": [HumanMessage(content=req.message)]})
    final = result["messages"][-1]
    content = final.content
    if isinstance(content, list):
        content = "\n".join(
            item.get("text", str(item)) if isinstance(item, dict) else str(item)
            for item in content
            if item
        )
    return {"output": content or "No response received."}


@app.get("/health")
def health():
    """Return a simple health-check response."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8300))
    uvicorn.run(app, host="0.0.0.0", port=port)
