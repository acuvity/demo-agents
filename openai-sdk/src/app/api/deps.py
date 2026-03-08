from __future__ import annotations

from fastapi import HTTPException, Request

from app.runtime.agent_runtime import AgentRuntime


def get_runtime(request: Request) -> AgentRuntime:
    runtime = getattr(request.app.state, "runtime", None)
    if runtime is None:
        raise HTTPException(status_code=503, detail="Agent runtime is not initialized")
    return runtime