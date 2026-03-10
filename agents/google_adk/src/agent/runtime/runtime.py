"""Google ADK runtime for managing agent sessions and message dispatch."""

import logging
import sys
from typing import Any, cast

from dotenv import load_dotenv
from google.adk.agents import LlmAgent  # pylint: disable=import-error,no-name-in-module
from google.adk.models.lite_llm import LiteLlm  # pylint: disable=import-error,no-name-in-module
from google.adk.tools.mcp_tool import (  # pylint: disable=import-error,no-name-in-module
    McpToolset,
    SseConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.adk.runners import Runner  # pylint: disable=import-error,no-name-in-module
from google.adk.sessions import InMemorySessionService  # pylint: disable=import-error,no-name-in-module
from google.genai import types  # pylint: disable=import-error,no-name-in-module

from config import AgentConfig

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


class GoogleADKRuntime:
    """Manages the Google ADK agent, sessions, and message routing."""

    def __init__(self, cfg: AgentConfig) -> None:
        """Initialise the runtime with config, session service, and root agent."""
        self.cfg = cfg
        self.session_service = InMemorySessionService()
        self.mcp_toolsets = self.setup_mcp_toolsets()
        self.app_name: str = cfg["app_name"]

        self.root_agent = LlmAgent(
            model=LiteLlm(model="anthropic/claude-sonnet-4-6"),
            name="research_assistant",
            description="A research assistant that can search the web and sequential thinking",
            instruction=self.cfg["instruction"],
            tools=cast(list[Any], self.mcp_toolsets),
        )
        self.runner = Runner(
            agent=self.root_agent,
            app_name=self.app_name,
            session_service=self.session_service,
        )

    def setup_mcp_toolsets(self) -> list[McpToolset]:
        """Build and return the list of MCP toolsets defined in config."""
        toolsets: list[McpToolset] = []
        if not self.cfg["mcp_servers"]:
            return toolsets
        for server in self.cfg["mcp_servers"]:
            url: str = server["url"]
            connection_params: SseConnectionParams | StreamableHTTPConnectionParams
            if url.rstrip("/").endswith("/sse"):
                connection_params = SseConnectionParams(
                    url=url,
                    timeout=60,
                    sse_read_timeout=6500,
                )
            else:
                connection_params = StreamableHTTPConnectionParams(
                    url=url,
                    timeout=60,
                    sse_read_timeout=6500,
                )
            toolsets.append(McpToolset(connection_params=connection_params))
        return toolsets

    # TODO: handle errors and exceptions, retries, and timeouts  # pylint: disable=fixme
    async def send(self, user_input: str) -> str:
        """Send a message to the agent and return the final response text."""
        # TODO: derive user from JWT token; reuse existing session if present  # pylint: disable=fixme
        user_id = "default_user"

        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_input)],
        )

        response_text = ""
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[-1].text or ""

        return response_text
