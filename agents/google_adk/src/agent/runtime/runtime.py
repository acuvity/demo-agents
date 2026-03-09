import logging
import os
import sys

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, SseConnectionParams, StreamableHTTPConnectionParams

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from google.genai import types

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

class GoogleADKRuntime:

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.session_service = InMemorySessionService()
        self.mcp_toolsets = self.setup_mcp_toolsets()
        self.app_name = cfg["app_name"]

        self.root_agent = LlmAgent(
            model=LiteLlm(model="anthropic/claude-sonnet-4-6"),
            name="research_assistant",
            description="A research assistant that can search the web and sequential thinking",
            instruction=self.cfg["instruction"],
            tools=self.mcp_toolsets,
        )
        self.runner = Runner(
            agent=self.root_agent,
            app_name=self.app_name,
            session_service=self.session_service,

        )

    def setup_mcp_toolsets(self) -> list[McpToolset]:
        toolsets: list[McpToolset] = []
        if not self.cfg.get("mcp_servers"):
            return toolsets
        for server in self.cfg["mcp_servers"]:
            if server["url"].rstrip("/").endswith("/sse"):
                connection_params = SseConnectionParams(
                    url=server["url"],
                    timeout=30,
                    sse_read_timeout=300,
                )
            else:
                connection_params = StreamableHTTPConnectionParams(
                    url=server["url"],
                    timeout=30,
                    sse_read_timeout=300,
                )
            toolsets.append(
                McpToolset(connection_params=connection_params)
            )       
        return toolsets

    # todo handle errors and exceptions and retries and timeouts    
    async def send(self, input: str) -> str:
        # todo: derive the user from jwt token and check if the user has an existing session, if not, create a new session
        user_id="default_user"

        session = await self.session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,            
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=input)],
        )

        response_text = ""
        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[-1].text

        return response_text
