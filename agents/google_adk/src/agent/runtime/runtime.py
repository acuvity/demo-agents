"""Google ADK runtime for managing agent sessions and message dispatch."""

import logging
import sys
from typing import Any, cast
import os

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

        litellm_api_base: str | None = cfg["litellm"]["api_base"]
        litellm_api_key: str | None = cfg["litellm"]["api_key"]

        if cfg.get("mode") == "gateway":
            logger.info("Using AI Gateway config")
            gateway_root = self._gateway_base_url()
            gateway_llm_route = cfg.get("gateway_llm_route") or "anthropic-api"
            model = LiteLlm(
                model="anthropic/claude-sonnet-4-6",
                api_base=f"{gateway_root}/{gateway_llm_route}",
                extra_headers={"Authorization": f"Bearer {self._gateway_token()}"},
                # apex owns upstream auth on the gateway path and strips/replaces
                # any provider API-key header the client sends (see apex's
                # aigateway request handler) — this placeholder only satisfies
                # litellm's own client-side "an api_key must be set" check.
                api_key="acuvity-gateway-managed",
            )
        elif litellm_api_base:
            logger.info("Using litellm proxy config")
            model = LiteLlm(
                model="claude-sonnet-4-6",
                api_key=litellm_api_key if litellm_api_key else None,
                api_base=litellm_api_base,  # pyright: ignore[reportUnknownArgumentType]
            )
        else:
            model = LiteLlm(model="anthropic/claude-sonnet-4-6")

        self.root_agent = LlmAgent(
            model=model,
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

    def _gateway_base_url(self) -> str:
        """Return the configured AI Gateway root URL, e.g. https://<apex-host>/<org>/<gw>."""
        base_url = self.cfg.get("gateway_base_url")
        if not base_url:
            raise ValueError("mode is 'gateway' but gateway_base_url is not set in config")
        return base_url

    def _gateway_token(self) -> str:
        """Return the app-component token used to authenticate to the AI Gateway."""
        token = os.environ.get("GOOGLE_ADK_AGENT_TOKEN")
        if not token:
            raise ValueError("mode is 'gateway' but GOOGLE_ADK_AGENT_TOKEN is not set")
        return token

    def _build_mcp_toolset(self, url: str, headers: dict[str, str] | None) -> McpToolset:
        """Build a single MCP toolset for the given URL, choosing transport by URL shape."""
        connection_params: SseConnectionParams | StreamableHTTPConnectionParams
        if url.rstrip("/").endswith("/sse"):
            connection_params = SseConnectionParams(
                url=url,
                timeout=60,
                sse_read_timeout=6500,
                headers=headers,
            )
        else:
            connection_params = StreamableHTTPConnectionParams(
                url=url,
                timeout=60,
                sse_read_timeout=6500,
                headers=headers,
            )
        return McpToolset(connection_params=connection_params)

    def setup_mcp_toolsets(self) -> list[McpToolset]:
        """Build and return the list of MCP toolsets defined in config.

        Arcade is a third-party MCP gateway (api.arcade.dev) that is never
        proxied through apex, so it's split out and handled identically
        regardless of mode. Every other configured server is "apex-fronted":
        in gateway mode they're all served behind one shared AI Gateway MCP
        endpoint (tools disambiguated by a provider-name prefix apex adds),
        so gateway mode builds exactly one toolset for all of them combined
        rather than one per configured URL.
        """
        servers = self.cfg["mcp_servers"] or []
        passthrough = [s for s in servers if s["name"] == "arcade-mcp-gateway"]
        apex_fronted = [s for s in servers if s["name"] != "arcade-mcp-gateway"]

        toolsets: list[McpToolset] = []

        if self.cfg.get("mode") == "gateway":
            if apex_fronted:
                toolsets.append(
                    self._build_mcp_toolset(
                        url=f"{self._gateway_base_url()}/mcp",
                        headers={"Authorization": f"Bearer {self._gateway_token()}"},
                    )
                )
        else:
            for server in apex_fronted:
                toolsets.append(self._build_mcp_toolset(url=server["url"], headers=None))

        for server in passthrough:
            arcade_user_id: str | None = self.cfg["arcade"]["user_id"]
            if os.environ.get("ARCADE_API_KEY") and arcade_user_id:
                headers = {
                    "Authorization": f"Bearer {os.environ['ARCADE_API_KEY']}",
                    "Arcade-User-ID": arcade_user_id,
                }
                toolsets.append(self._build_mcp_toolset(url=server["url"], headers=headers))
            else:
                logger.debug("No Aracde credentials set, skipping arcade mcp url")

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
