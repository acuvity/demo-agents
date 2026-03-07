"""Runtime for the OpenAI SDK agent."""

import logging
import sys
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from agents.mcp import MCPServer, MCPServerSse
from config import AgentConfig, McpServerConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class OpenAISDKRuntime:
    """Runtime that manages the OpenAI SDK agent and MCP server connections."""

    def __init__(self, cfg: AgentConfig):
        self.cfg = cfg
        self.app_name = cfg["app_name"]
        self.agent = Agent(
            name="openai-sdk-mcp-agent",
            instructions=self.cfg["instruction"],
            model=LitellmModel(model="anthropic/claude-sonnet-4-20250514"),
        )

    async def setup_mcp_toolsets(self, stack: AsyncExitStack) -> list[MCPServer]:
        """Connect to configured MCP servers and return the list of connected servers."""
        servers_cfg: list[McpServerConfig] = self.cfg.get("mcp_servers") or []

        if not servers_cfg:
            logger.warning(
                "No 'mcp_servers' entries found in config – "
                "agent will run without any MCP tools."
            )
            return []

        connected_servers: list[MCPServer] = []

        for entry in servers_cfg:
            name: str = entry.get("name") or entry.get("url", "unnamed-mcp")
            url: str | None = entry.get("url")

            if not url:
                logger.warning("MCP server entry '%s' has no 'url' – skipping.", name)
                continue

            server = MCPServerSse(
                name=name,
                params={
                    "url": url,
                    "headers": entry.get("headers") or {},
                    "timeout": float(entry.get("timeout", 30)),
                },
                cache_tools_list=bool(entry.get("cache_tools", False)),
            )

            try:
                await stack.enter_async_context(server)
                connected_servers.append(server)
                logger.info("mcp: connected server  name='%s'  url='%s'", name, url)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error("MCP server '%s' failed to connect: %s", name, e)

        if not connected_servers:
            logger.warning(
                "No MCP servers connected – agent will run without any MCP tools."
            )

        return connected_servers

    async def send(self, user_input: str) -> str:
        """Send a message to the agent and return the final output."""
        async with AsyncExitStack() as stack:
            connected_servers = await self.setup_mcp_toolsets(stack)
            self.agent.mcp_servers = connected_servers

            result = await Runner.run(
                self.agent,
                input=user_input,
                max_turns=20,
            )

            return str(result.final_output)
