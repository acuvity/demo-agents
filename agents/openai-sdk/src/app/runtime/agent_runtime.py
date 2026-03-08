from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass
from typing import Any

from agents import Agent, OpenAIChatCompletionsModel, Runner
from agents.extensions.models.litellm_model import LitellmModel
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

from app.config.loader import info, warn

try:
    from opentelemetry import trace
except ImportError:  # pragma: no cover
    trace = None


logger = logging.getLogger("uvicorn.error")


def build_model(cfg: dict):
    llm_cfg: dict = cfg.get("llm", {})
    provider: str = llm_cfg.get("provider", "openai").lower()

    if provider == "openai":
        oa_cfg = llm_cfg.get("openai") or {}
        model_name: str = oa_cfg.get("model", "gpt-4o-mini")
        api_key: str | None = oa_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY")
        base_url: str | None = oa_cfg.get("base_url") or None

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        model = OpenAIChatCompletionsModel(model=model_name, openai_client=client)

        info(f"model: OpenAI  model='{model_name}'  base_url={base_url or 'default'}")

        return model

    if provider == "claude":
        from agents import set_tracing_disabled

        set_tracing_disabled(True)

        cl_cfg = llm_cfg.get("claude") or {}
        model_name = cl_cfg.get("model", "claude-sonnet-4-20250514")
        api_key = cl_cfg.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")

        if api_key:
            os.environ.setdefault("ANTHROPIC_API_KEY", api_key)

        model = LitellmModel(model=f"anthropic/{model_name}", api_key=api_key)

        info(f"model: Claude (via litellm)  model='{model_name}'")

        return model

    raise ValueError(
        f"Unknown LLM provider: '{provider}'. Choose 'openai' or 'claude'."
    )


async def probe_mcp_url(url: str, headers: dict, timeout: float) -> bool:
    import httpx

    try:
        async with httpx.AsyncClient(headers=headers, timeout=min(timeout, 5.0)) as client:
            await client.get(url)
        return True
    except Exception:
        return False


async def build_mcp_servers(cfg: dict) -> list[MCPServerStreamableHttp]:
    servers_cfg: list[dict] = cfg.get("mcp_servers") or []

    if not servers_cfg:
        warn(
            "No 'mcp_servers' entries found in config – "
            "agent will run without any MCP tools."
        )
        return []

    servers: list[MCPServerStreamableHttp] = []

    for entry in servers_cfg:
        name: str = entry.get("name") or entry.get("url", "unnamed-mcp")
        url: str | None = entry.get("url")

        if not url:
            warn(f"MCP server entry '{name}' has no 'url' – skipping.")
            continue

        headers: dict = entry.get("headers") or {}
        timeout: float = float(entry.get("timeout", 30))
        cache_tools: bool = bool(entry.get("cache_tools", False))

        if not await probe_mcp_url(url, headers, timeout):
            warn(
                f"MCP server '{name}' at '{url}' is not reachable – "
                "skipping this server."
            )
            continue

        params: MCPServerStreamableHttpParams = {
            "url": url,
            "headers": headers,
            "timeout": timeout,
        }

        server = MCPServerStreamableHttp(
            name=name,
            params=params,
            cache_tools_list=cache_tools,
        )

        servers.append(server)

        info(f"mcp: registered server  name='{name}'  url='{url}'")

    if not servers:
        warn(
            "None of the configured MCP servers could be reached – "
            "agent will run without any MCP tools."
        )

    return servers


@dataclass
class AgentRuntime:
    cfg: dict
    agent: Agent
    otel_provider: Any | None

    async def chat(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_turns: int = 20,
    ) -> str:

        if system_prompt:
            agent = Agent(
                name=self.agent.name,
                instructions=system_prompt,
                model=self.agent.model,
                mcp_servers=self.agent.mcp_servers,
            )
        else:
            agent = self.agent

        # If OTEL is available create a span around agent execution
        if trace is not None:
            tracer = trace.get_tracer(__name__)
            span_ctx = tracer.start_as_current_span("agent.run")
        else:
            span_ctx = contextlib.nullcontext()

        with span_ctx as span:

            # Attach useful attributes for debugging
            if span is not None and hasattr(span, "set_attribute"):
                span.set_attribute("agent.prompt", prompt)
                span.set_attribute("agent.prompt_length", len(prompt))
                span.set_attribute("agent.max_turns", max_turns)

                if system_prompt:
                    span.set_attribute("agent.system_prompt", system_prompt)

                provider = self.cfg.get("llm", {}).get("provider", "unknown")
                span.set_attribute("agent.llm_provider", provider)

            result = await Runner.run(
                agent,
                input=prompt,
                max_turns=max_turns,
            )

        if self.otel_provider is not None:
            self.otel_provider.force_flush()

        return str(result.final_output)


async def create_runtime(cfg: dict) -> AgentRuntime:
    model = build_model(cfg)
    mcp_servers = await build_mcp_servers(cfg)

    agent = Agent(
        name="openai-sdk-mcp-agent",
        instructions=(
            "You are a helpful assistant. "
            "Use the available MCP tools whenever they can help answer the user's request."
        ),
        model=model,
        mcp_servers=mcp_servers,
    )

    return AgentRuntime(
        cfg=cfg,
        agent=agent,
        otel_provider=None,
    )