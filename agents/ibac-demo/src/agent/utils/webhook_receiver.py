"""Local webhook capture server for demo tools.

Receives POST /webhook and POST /sync calls from post_webhook() and
sync_with_external_system() MCP tools. Stores every event in memory and
exposes GET /events so you can inspect captured payloads in the browser or
with curl.

Run:
    uv run python3 utils/webhook_receiver.py

Default port: 9000 (override with WEBHOOK_PORT env var).
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

_agent_root = Path(__file__).resolve().parent.parent
if str(_agent_root) not in sys.path:
    sys.path.insert(0, str(_agent_root))

app = FastAPI(title="Demo Webhook Receiver")

_events: list[dict[str, Any]] = []


def _capture(route: str, request_body: Any) -> None:
    _events.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "route": route,
            "body": request_body,
        }
    )


@app.post("/webhook")
async def receive_webhook(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = (await request.body()).decode()
    _capture("/webhook", body)
    print(f"[WEBHOOK RECEIVED] /webhook  payload={str(body)[:300]}")
    return JSONResponse({"status": "ok", "received": True, "event_count": len(_events)})


@app.post("/sync")
async def receive_sync(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = (await request.body()).decode()
    _capture("/sync", body)
    print(f"[WEBHOOK RECEIVED] /sync  payload={str(body)[:300]}")
    return JSONResponse({"status": "ok", "synced": True, "endpoint_ack": True, "event_count": len(_events)})


@app.get("/events")
async def list_events() -> JSONResponse:
    return JSONResponse({"total": len(_events), "events": _events})


@app.delete("/events")
async def clear_events() -> JSONResponse:
    _events.clear()
    return JSONResponse({"status": "cleared"})


if __name__ == "__main__":
    port = int(os.environ.get("WEBHOOK_PORT", "9000"))
    host = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
    print(f"[webhook-receiver] listening on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
