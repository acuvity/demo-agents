import logging
import os
import sys

import yaml
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, SseConnectionParams, StreamableHTTPConnectionParams

from utils import setup_otel

_RUNTIME_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_RUNTIME_DIR)

load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_mcp_toolsets(cfg: dict) -> list[McpToolset]:
    toolsets: list[McpToolset] = []
    for server in cfg["mcp_servers"]:
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


cfg = load_config(os.path.join(_BACKEND_DIR, "config.yaml"))
setup_otel(cfg)
mcp_toolsets = setup_mcp_toolsets(cfg)

root_agent = LlmAgent(
    model=LiteLlm(model="anthropic/claude-sonnet-4-6"),
    name="research_assistant",
    description="A research assistant that can search the web and sequential thinking",
    instruction=cfg["instruction"],
    tools=mcp_toolsets,
)


def create_fastapi_app():
    from fastapi import FastAPI
    from pydantic import BaseModel
    from starlette.middleware.cors import CORSMiddleware
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name=cfg["app_name"],
        session_service=session_service,
    )

    app = FastAPI(title=cfg["title"])
    FastAPIInstrumentor.instrument_app(app)

    cors_origins = cfg["cors_origins"]
    origins = (
        [o.strip() for o in cors_origins.split(",")]
        if isinstance(cors_origins, str)
        else cors_origins
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class MessageRequest(BaseModel):
        message: str

    @app.post("/send")
    async def send_message(req: MessageRequest):
        session = await session_service.create_session(
            app_name=cfg["app_name"],
            user_id=cfg.get("user_id", "default_user"),
        )

        content = types.Content(
            role="user",
            parts=[types.Part.from_text(text=req.message)],
        )

        response_text = ""
        async for event in runner.run_async(
            user_id=cfg.get("user_id", "default_user"),
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[-1].text

        return {"output": response_text}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
