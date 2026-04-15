"""LLM and MCP configuration builders."""
# Imports are lazy per provider to avoid loading unused stacks.
# pylint: disable=import-outside-toplevel
import os
import sys
from typing import Any

from utils.paths import get_agent_root


def _debug_llm_fingerprint(key_source: str, api_key: str, model_line: str) -> None:
    """When DEBUG_LLM=1, print which env var supplied the key (last 4 chars only) and model."""
    if os.environ.get("DEBUG_LLM") != "1":
        return
    tail = api_key[-4:] if len(api_key) >= 4 else "****"
    print(
        f"DEBUG_LLM: key_source={key_source} key_tail=...{tail} {model_line}",
        file=sys.stderr,
        flush=True,
    )


def build_llm(tools):
    """Build the LLM based on LLM_PROVIDER env var.

    Supported providers:
    - anthropic (default): uses ANTHROPIC_API_KEY; LLM_BASE_URL overrides the endpoint.
    - openai: uses OPENAI_API_KEY; LLM_BASE_URL enables any OpenAI-compatible endpoint.
    - openrouter: uses OPENROUTER_API_KEY via the OpenRouter API.

    LLM_API_KEY overrides the provider-specific key for all providers.
    LLM_MODEL overrides the default model name.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic")
    base_url = os.environ.get("LLM_BASE_URL")
    api_key_override = os.environ.get("LLM_API_KEY")

    if provider == "openrouter":
        from langchain_openrouter import ChatOpenRouter  # type: ignore[import]

        model_name = os.environ.get("OPENROUTER_MODEL", "stepfun/step-3.5-flash")
        api_key = api_key_override or os.environ["OPENROUTER_API_KEY"]
        key_src = "LLM_API_KEY" if api_key_override else "OPENROUTER_API_KEY"
        _debug_llm_fingerprint(key_src, api_key, f"OPENROUTER_MODEL={model_name}")
        return ChatOpenRouter(
            model=model_name,
            api_key=api_key,  # type: ignore[arg-type]
            temperature=0,
        ).bind_tools(tools)

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        model_name = os.environ.get("LLM_MODEL", "gpt-4o")
        api_key = api_key_override or os.environ["OPENAI_API_KEY"]
        key_src = "LLM_API_KEY" if api_key_override else "OPENAI_API_KEY"
        _debug_llm_fingerprint(key_src, api_key, f"LLM_MODEL={model_name}")
        kwargs: dict[str, Any] = {"model": model_name, "api_key": api_key, "temperature": 0}
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs).bind_tools(tools)

    from langchain_anthropic import ChatAnthropic

    model_name = os.environ.get("LLM_MODEL", "claude-opus-4-6")
    api_key = api_key_override or os.environ["ANTHROPIC_API_KEY"]
    key_src = "LLM_API_KEY" if api_key_override else "ANTHROPIC_API_KEY"
    _debug_llm_fingerprint(key_src, api_key, f"LLM_MODEL={model_name}")
    kwargs = {"model_name": model_name, "api_key": api_key, "temperature": 0}
    if base_url:
        kwargs["base_url"] = base_url

    return ChatAnthropic(**kwargs).bind_tools(tools)  # type: ignore[call-arg, arg-type]


def build_mcp_config() -> dict:
    """Build the MCP client config based on MCP_SERVER env var (arcade or local)."""
    server = os.environ.get("MCP_SERVER", "arcade")

    if server == "local":
        sse_url = os.environ.get("LOCAL_MCP_SSE_URL")
        if sse_url:
            return {
                "local": {
                    "url": sse_url,
                    "transport": "sse",
                    "read_timeout_seconds": 65534,
                    "read_transport_sse_timeout_seconds": 65534,
                }
            }
        return {
            "local": {
                "command": "uv",
                "args": ["run", "python3", "tools/mcp_tools.py"],
                "transport": "stdio",
                "cwd": str(get_agent_root()),
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
