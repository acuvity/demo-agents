"""FastAPI entrypoint for the simple-langgraph demo agent."""
import asyncio
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition

from utils.acuvity_errors import policy_block_from_exception
from utils.config import build_llm, build_mcp_config
from utils.demo_prompts_ui import load_demo_cards_for_api
from utils.paths import get_upload_dir

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

SYSTEM_PROMPT = (
    "You are an AI assistant that uses tools.\n\n"
    "CRITICAL RULE:\n"
    "- You MUST base your answer on tool output(s).\n"
    "- Your answer MUST be SOLELY based on the tool output(s).\n"
)

UPLOAD_DIR = get_upload_dir()

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
    """Request body for JSON /send."""

    message: str


def _append_pdf_hint(message: str, saved_abs: str) -> str:
    hint = (
        f"\n\n[Attached PDF on server: {saved_abs}]\n"
        "Use the parse_file tool with this exact file_path to extract text, "
        "then fulfill the user's request."
    )
    base = message.strip()
    if not base:
        return (
            "I attached a PDF. Please parse it and help me based on its contents."
            + hint
        )
    return (base + hint).strip()


async def _run_agent(message: str) -> dict:
    try:
        agent = await get_agent()
        result = await agent.ainvoke({"messages": [HumanMessage(content=message)]})
        final = result["messages"][-1]
        content = final.content
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in content
                if item
            )
        return {
            "blocked": False,
            "output": content or "No response received.",
        }
    except HTTPException:
        raise
    except Exception as e:
        blocked_payload = policy_block_from_exception(e)
        if blocked_payload is not None:
            return blocked_payload
        logging.warning(
            "Agent error not classified as gateway policy block (%s). "
            "Set DEBUG_ACUVITY_BLOCKS=1 on the server for full exception chain and body snippets, "
            "or ACUVITY_BLOCK_HTTP_STATUSES=400 (comma-separated) if Apex uses a status we do not map by default.",
            type(e).__name__,
        )
        logging.exception("Agent run failed")
        raise HTTPException(
            status_code=500,
            detail="Agent failed while processing your request.",
        ) from None


@app.post("/send")
async def send_message(request: Request):
    """Accept JSON {message} or multipart form (message + optional PDF file)."""
    content_type = request.headers.get("content-type", "")

    saved_abs: str | None = None

    if content_type.startswith("application/json"):
        body = await request.json()
        req = MessageRequest.model_validate(body)
        text = req.message.strip()
        if not text:
            raise HTTPException(status_code=400, detail="message is required")
        return await _run_agent(text)

    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        raw_msg = form.get("message")
        text = (raw_msg if isinstance(raw_msg, str) else str(raw_msg or "")).strip()
        upload = form.get("file")
        if isinstance(upload, list):
            upload = upload[0] if upload else None

        # Starlette's multipart parser returns starlette.datastructures.UploadFile.
        # fastapi.UploadFile subclasses that type, so checking Starlette accepts both.
        if upload is not None and isinstance(upload, StarletteUploadFile):
            name = upload.filename or "upload.pdf"
            if not name.lower().endswith(".pdf"):
                raise HTTPException(
                    status_code=400,
                    detail="Only PDF attachments are supported (.pdf).",
                )
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            dest = UPLOAD_DIR / f"{uuid.uuid4().hex}.pdf"
            try:
                dest.write_bytes(await upload.read())
            except Exception:
                logging.exception("Failed to read or save uploaded PDF")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save the uploaded file.",
                ) from None
            saved_abs = str(dest.resolve())
            logging.info("Saved PDF upload to %s", saved_abs)

        if not text.strip() and not saved_abs:
            raise HTTPException(
                status_code=400,
                detail="Send a non-empty message and/or attach a PDF.",
            )

        full_message = _append_pdf_hint(text, saved_abs) if saved_abs else text
        return await _run_agent(full_message)

    raise HTTPException(
        status_code=415,
        detail="Use Content-Type: application/json or multipart/form-data.",
    )


@app.get("/health")
def health():
    """Return a simple health-check response."""
    return {"status": "ok"}


@app.get("/scenarios")
def list_demo_scenarios():
    """Home-screen cards from prompt-scenarios/demo-prompts.txt (CWD-independent)."""
    return load_demo_cards_for_api()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8300))
    uvicorn.run(app, host="0.0.0.0", port=port)
