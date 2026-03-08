"""google_adk/agent.py — Single entry point for ADK web and FastAPI modes.

Usage:
    ADK web (local):  adk web google_adk          (imports root_agent automatically)
    FastAPI server:   python agent.py --mode fastapi [--host 0.0.0.0] [--port 8300]
"""

import logging
import os
import sys

_AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AGENT_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(_AGENT_DIR, ".env"))

import yaml
from opentelemetry import trace
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.threading import ThreadingInstrumentor
from openinference.instrumentation.mcp import MCPInstrumentor
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from openinference.instrumentation.litellm import LiteLLMInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset

from utils.mcp_conn import mcp_connection_params
from utils import FileSpanExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def setup_otel(cfg: dict):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    existing = trace.get_tracer_provider()
    if isinstance(existing, TracerProvider):
        provider = existing
    else:
        underlying = getattr(existing, "_real_provider", None)
        if isinstance(underlying, TracerProvider):
            provider = underlying
        else:
            from opentelemetry.sdk.resources import Resource, SERVICE_NAME

            provider = TracerProvider(
                resource=Resource.create(
                    {SERVICE_NAME: cfg["otel"]["service_name"]}
                )
            )
            trace.set_tracer_provider(provider)

    if cfg["otel"]["enabled"]:
        if cfg["otel"]["console_export"]:
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        if not cfg["otel"]["no_file_export"]:
            provider.add_span_processor(
                SimpleSpanProcessor(FileSpanExporter(file_path=cfg["otel"]["file"]))
            )

        otlp_endpoint = cfg["otel"]["otlp_endpoint"]
        send_spans = cfg["otel"]["send_spans"]
        if otlp_endpoint and send_spans:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                insecure=cfg["otel"]["insecure"],
            )
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
            logger.info(
                f"OTLP exporter configured: endpoint={otlp_endpoint}, insecure={cfg['otel']['insecure']}"
            )

    for instrumentor in cfg["otel"]["instrumentors"]:
        if instrumentor == "HTTPXClientInstrumentor":
            HTTPXClientInstrumentor().instrument()
        elif instrumentor == "AioHttpClientInstrumentor":
            AioHttpClientInstrumentor().instrument()
        elif instrumentor == "ThreadingInstrumentor":
            ThreadingInstrumentor().instrument()
        elif instrumentor == "MCPInstrumentor":
            MCPInstrumentor().instrument()
        elif instrumentor == "GoogleADKInstrumentor":
            GoogleADKInstrumentor().instrument()
        elif instrumentor == "LiteLLMInstrumentor":
            LiteLLMInstrumentor().instrument()

    return provider


def setup_mcp_toolsets(cfg: dict) -> list[McpToolset]:
    toolsets: list[McpToolset] = []
    for server in cfg["mcp_servers"]:
        toolsets.append(
            McpToolset(connection_params=mcp_connection_params(server["url"]))
        )
    return toolsets


cfg = load_config(os.path.join(_AGENT_DIR, "config.yaml"))
setup_otel(cfg)
mcp_toolsets = setup_mcp_toolsets(cfg)

root_agent = LlmAgent(
    model=LiteLlm(model="anthropic/claude-sonnet-4-6"),
    name="research_assistant",
    description="A research assistant that can search the web and read from a database",
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


if __name__ == "__main__":
    import uvicorn

    app = create_fastapi_app()
    uvicorn.run(app, host="0.0.0.0", port=8300)

