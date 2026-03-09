import logging
import sys
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from agents.mcp import MCPServerSse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

class OpenAISDKRuntime:

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.app_name = cfg["app_name"]
        self.agent = Agent(
            name="openai-sdk-mcp-agent",
            instructions=self.cfg["instruction"],
            model=LitellmModel(model="anthropic/claude-sonnet-4-20250514"),
        )

    async def setup_mcp_toolsets(self, stack: AsyncExitStack) -> list[MCPServerSse]:
        servers_cfg: list[dict] = self.cfg.get("mcp_servers") or []

        if not servers_cfg:
            logger.warning(
                "No 'mcp_servers' entries found in config – "
                "agent will run without any MCP tools."
            )
            return []

        connected_servers: list[MCPServerSse] = []

        for entry in servers_cfg:
            name: str = entry.get("name") or entry.get("url", "unnamed-mcp")
            url: str | None = entry.get("url")

            if not url:
                logger.warning(f"MCP server entry '{name}' has no 'url' – skipping.")
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
                logger.info(f"mcp: connected server  name='{name}'  url='{url}'")
            except Exception as e:
                logger.error(f"MCP server '{name}' failed to connect: {e}")

        if not connected_servers:
            logger.warning(
                "No MCP servers connected – agent will run without any MCP tools."
            )

        return connected_servers

    async def send(self, input: str) -> str:
        async with AsyncExitStack() as stack:
            connected_servers = await self.setup_mcp_toolsets(stack)
            self.agent.mcp_servers = connected_servers

            result = await Runner.run(
                self.agent,
                input=input,
                max_turns=20,
            )

            return str(result.final_output)
