from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.config.loader import load_config
from app.observability.logging_utils import configure_logging
from app.observability.otel import instrument_fastapi_app, setup_otel
from app.runtime.agent_runtime import create_runtime

configure_logging()
logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    config_path = os.environ.get("AGENT_CONFIG", "config.yaml")

    logger.info("Initializing agent runtime with config: %s", config_path)

    cfg = load_config(config_path)

    setup_otel(cfg)

    instrument_fastapi_app(app)

    app.state.runtime = await create_runtime(cfg)

    try:
        yield
    finally:
        logger.info("Shutting down agent runtime")
        app.state.runtime = None


app = FastAPI(
    title="MCP Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
