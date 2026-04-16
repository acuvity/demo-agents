"""FastAPI entrypoint for the simple-langgraph demo agent."""
import asyncio
import logging
import os
import uuid
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from starlette.datastructures import UploadFile as StarletteUploadFile
from starlette.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.acuvity_errors import policy_block_from_exception
from utils.agent_graph import compile_tool_bound_graph
from utils.config import build_llm, build_mcp_config
from utils.demo_prompts_ui import load_demo_cards_for_api
from utils.paths import get_upload_dir

logging.getLogger("mcp.client.streamable_http").setLevel(logging.ERROR)

UPLOAD_DIR = get_upload_dir()

app = FastAPI(title="Simple LangGraph Demo Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_lock = asyncio.Lock()
# Mutable singleton without `global` (pylint-friendly).
_COMPILED_AGENT: dict[str, Any] = {"value": None}


async def get_agent() -> Any:
    """Lazily initialize and return the compiled LangGraph agent."""
    async with _lock:
        if _COMPILED_AGENT["value"] is None:
            mcp_client = MultiServerMCPClient(build_mcp_config())
            tools = await mcp_client.get_tools()
            model = build_llm(tools)
            _COMPILED_AGENT["value"] = compile_tool_bound_graph(model, tools)
            logging.info("Agent initialized with %d tools", len(tools))
    return _COMPILED_AGENT["value"]


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


def _proxy_tunnel_http_status(exc: BaseException) -> int | None:
    """If the chain contains httpx/httpcore ProxyError with 401 or 407, return that code."""
    for link in _walk_exception_chain(exc):
        if type(link).__name__ != "ProxyError":
            continue
        text = str(link)
        if "407" in text:
            return 407
        if "401" in text:
            return 401
    return None


def _walk_exception_chain(exc: BaseException):
    """Yield exception and __cause__ / __context__ links (deduped by id)."""
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        yield cur
        seen.add(id(cur))
        nxt = cur.__cause__
        if nxt is None:
            nxt = cur.__context__
        cur = nxt if isinstance(nxt, BaseException) else None


def _proxy_env_summary() -> str:
    raw = (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "").strip()
    if not raw:
        return "HTTPS_PROXY/HTTP_PROXY=(unset)"
    try:
        p = urlparse(raw)
        host = p.hostname or "?"
        port_suffix = f":{p.port}" if p.port else ""
        return f"proxy_target={p.scheme}://[token_redacted]{host}{port_suffix}"
    except (TypeError, ValueError):
        return "HTTPS_PROXY/HTTP_PROXY=(set, could not parse)"


def _log_upstream_http_debug(exc: BaseException) -> None:
    """When DEBUG_PROXY_UPSTREAM=1 and a proxy is configured, log HTTP details per chain link."""
    if os.environ.get("DEBUG_PROXY_UPSTREAM", "").strip() not in ("1", "true", "yes"):
        return
    if not (os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")):
        return
    lines = [
        "DEBUG_PROXY_UPSTREAM: upstream error detail (compare response URL host to api.openai.com, "
        "openrouter.ai, or your Apex; body may be Acuvity or vendor)",
        _proxy_env_summary(),
    ]
    for i, link in enumerate(_walk_exception_chain(exc)):
        mod = type(link).__module__
        name = type(link).__name__
        lines.append(f"  [{i}] {mod}.{name}: {link!r}")
        resp = getattr(link, "response", None)
        if resp is not None:
            req = getattr(resp, "request", None)
            url = getattr(req, "url", None) if req is not None else None
            status = getattr(resp, "status_code", None)
            body = ""
            try:
                body = (getattr(resp, "text", None) or "")[:8000]
            except (OSError, TypeError, ValueError) as read_err:
                body = f"(unreadable: {read_err})"
            lines.append(f"      http_status={status!r} request_url={url!r}")
            lines.append(f"      response_body={body!r}")
        body_only = getattr(link, "body", None)
        if isinstance(body_only, str) and body_only.strip() and resp is None:
            lines.append(f"      exc.body={body_only[:4000]!r}")
    logging.error("\n".join(lines))


def _openrouter_api_error_response(exc: BaseException) -> tuple[int, str] | None:
    """OpenRouter LLM errors (403 is often account/team, not Acuvity policy)."""
    if type(exc).__name__ != "OpenRouterDefaultError":
        return None
    status = getattr(exc, "status_code", None)
    if not isinstance(status, int) or status < 400 or status > 599:
        status = 502
    body = getattr(exc, "body", None)
    if isinstance(body, str) and body.strip():
        detail = body.strip()
    else:
        msg = getattr(exc, "message", None)
        detail = str(msg).strip() if msg else str(exc)
    return status, f"OpenRouter: {detail}"


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
        _log_upstream_http_debug(e)
        proxy_tunnel = _proxy_tunnel_http_status(e)
        if proxy_tunnel == 401:
            logging.warning(
                "Acuvity proxy returned 401 (check ACUVITY_TOKEN, APEX_URL, and use "
                "run_ui.sh / run.sh so the token is percent-encoded in HTTPS_PROXY)."
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Acuvity proxy rejected credentials (401 Unauthorized). "
                    "Confirm ACUVITY_TOKEN and APEX_URL, then start via ./src/agent/run_ui.sh "
                    "(it URL-encodes the token for HTTPS_PROXY)."
                ),
            ) from e
        if proxy_tunnel == 407:
            logging.warning(
                "Acuvity proxy returned 407 Proxy Authentication Required (HTTPS_PROXY tunnel "
                "auth failed; not an LLM or Apex policy body)."
            )
            raise HTTPException(
                status_code=502,
                detail=(
                    "Acuvity proxy rejected tunnel authentication (407 Proxy Authentication "
                    "Required). The proxy did not accept the credentials embedded in HTTPS_PROXY "
                    "(wrong or expired ACUVITY_TOKEN, bad URL encoding, or org expects a "
                    "different proxy auth mode). Fix the token and restart via "
                    "./src/agent/run_ui.sh."
                ),
            ) from e
        or_err = _openrouter_api_error_response(e)
        if or_err is not None:
            ostatus, odetail = or_err
            logging.warning("OpenRouter API error (%s): %s", ostatus, odetail)
            raise HTTPException(status_code=ostatus, detail=odetail) from e
        blocked_payload = policy_block_from_exception(e)
        if blocked_payload is not None:
            return blocked_payload
        if isinstance(e, httpx.ProxyError):
            logging.warning(
                "Agent error: %s (proxy tunnel failure; not classified as Apex policy block). "
                "See DEBUG_PROXY_UPSTREAM=1 logs for proxy target.",
                type(e).__name__,
            )
        else:
            logging.warning(
                "Agent error not classified as gateway policy block (%s). "
                "Set DEBUG_ACUVITY_BLOCKS=1 on the server for full exception chain "
                "and body snippets, or ACUVITY_BLOCK_HTTP_STATUSES=400 (comma-separated) "
                "if Apex uses a status we do not map by default.",
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
