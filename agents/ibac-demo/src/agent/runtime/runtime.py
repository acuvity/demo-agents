"""ibac-demo agent runtime: MCP + LangGraph lifecycle and /send execution path."""
import asyncio
import logging
import os
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from utils.acuvity_errors import policy_block_from_exception
from utils.agent_graph import compile_tool_bound_graph
from utils.config import build_llm, build_mcp_config

logger = logging.getLogger(__name__)


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


class IbacDemoRuntime:  # pylint: disable=too-few-public-methods
    """Runtime for the ibac-demo LangGraph agent.

    Lazy MCP plus graph; same idea as langgraph runtime.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._compiled_agent: dict[str, Any] = {"value": None}

    async def _get_agent(self) -> Any:
        """Lazily initialize and return the compiled LangGraph agent."""
        async with self._lock:
            if self._compiled_agent["value"] is None:
                mcp_client = MultiServerMCPClient(build_mcp_config())
                tools = await mcp_client.get_tools()
                model = build_llm(tools)
                self._compiled_agent["value"] = compile_tool_bound_graph(model, tools)
                logger.info("Agent initialized with %d tools", len(tools))
        return self._compiled_agent["value"]

    async def run_turn(self, message: str) -> dict:
        """Run one user message through the graph; returns dict with output or blocked payload."""
        try:
            agent = await self._get_agent()
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
                logger.warning(
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
                logger.warning(
                    "Acuvity proxy returned 407 Proxy Authentication Required (HTTPS_PROXY tunnel "
                    "auth failed; not an LLM or Apex policy body)."
                )
                raise HTTPException(
                    status_code=502,
                    detail=(
                        "Acuvity proxy rejected tunnel authentication (407 Proxy Authentication "
                        "Required). The proxy did not accept the credentials embedded in "
                        "HTTPS_PROXY (wrong or expired ACUVITY_TOKEN, bad URL encoding, or org "
                        "expects a different proxy auth mode). Fix the token and restart via "
                        "./src/agent/run_ui.sh."
                    ),
                ) from e
            or_err = _openrouter_api_error_response(e)
            if or_err is not None:
                ostatus, odetail = or_err
                logger.warning("OpenRouter API error (%s): %s", ostatus, odetail)
                raise HTTPException(status_code=ostatus, detail=odetail) from e
            blocked_payload = policy_block_from_exception(e)
            if blocked_payload is not None:
                return blocked_payload
            if isinstance(e, httpx.ProxyError):
                logger.warning(
                    "Agent error: %s (proxy tunnel failure; not classified as Apex policy block). "
                    "See DEBUG_PROXY_UPSTREAM=1 logs for proxy target.",
                    type(e).__name__,
                )
            else:
                logger.warning(
                    "Agent error not classified as gateway policy block (%s). "
                    "Set DEBUG_ACUVITY_BLOCKS=1 on the server for full exception chain "
                    "and body snippets, or ACUVITY_BLOCK_HTTP_STATUSES=400 (comma-separated) "
                    "if Apex uses a status we do not map by default.",
                    type(e).__name__,
                )
            logger.exception("Agent run failed")
            raise HTTPException(
                status_code=500,
                detail="Agent failed while processing your request.",
            ) from None
