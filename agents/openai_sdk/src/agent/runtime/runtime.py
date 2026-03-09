import logging
import os
import sys

from dotenv import load_dotenv
from agents import Agent, Runner
from agents.extensions.models.litellm_model import LitellmModel
from agents.mcp import MCPServerStreamableHttp, MCPServerStreamableHttpParams

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
        self.mcp_toolsets = self.setup_mcp_toolsets()
        self.app_name = cfg["app_name"]

        self.root_agent = Agent(
            name="openai-sdk-mcp-agent",
            instructions=self.cfg["instruction"],
            model=LitellmModel(model="anthropic/claude-sonnet-4-20250514"),
            mcp_servers=self.mcp_toolsets,
        )

    def setup_mcp_toolsets(self) -> list[MCPServerStreamableHttp]:
        servers_cfg: list[dict] = self.cfg.get("mcp_servers") or []

        if not servers_cfg:
            logger.warning(
                "No 'mcp_servers' entries found in config – "
                "agent will run without any MCP tools."
            )
            return []

        servers: list[MCPServerStreamableHttp] = []

        for entry in servers_cfg:
            name: str = entry.get("name") or entry.get("url", "unnamed-mcp")
            url: str | None = entry.get("url")

            if not url:
                logger.warning(f"MCP server entry '{name}' has no 'url' – skipping.")
                continue

            headers: dict = entry.get("headers") or {}
            timeout: float = float(entry.get("timeout", 30))
            cache_tools: bool = bool(entry.get("cache_tools", False))

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

            logger.info(f"mcp: registered server  name='{name}'  url='{url}'")

        if not servers:
            logger.warning(
                "No MCP servers configured – agent will run without any MCP tools."
            )

        return servers



    async def send(self, input: str) -> str:
        result = await Runner.run(
            self.root_agent,
            input=input,
            max_turns=20,
        )

        return str(result.final_output)

