"""FastAPI entrypoint for the Google ADK agent service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor  # type: ignore[import-untyped]  # pylint: disable=import-error,no-name-in-module
from config import load_config_yaml
from observability import setup_otel
from runtime import OpenAISDKRuntime


cfg = load_config_yaml()

setup_otel(cfg)

app = FastAPI(title=cfg["title"])
runtime = OpenAISDKRuntime(cfg)

FastAPIInstrumentor.instrument_app(app)

cors_origins: str | list[str] = cfg["cors_origins"]
origins: list[str] = (
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
    """Request body for the /send endpoint."""

    message: str


@app.post("/send")
async def send_message(req: MessageRequest):
    """Handle an incoming chat message and return the agent response."""
    response_text = await runtime.send(req.message)
    return {"output": response_text}


@app.get("/health")
def health():
    """Return a simple health-check response."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8300)
