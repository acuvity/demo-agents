from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_runtime
from app.api.schemas import ChatRequest, ChatResponse
from app.runtime.agent_runtime import AgentRuntime

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    runtime: AgentRuntime = Depends(get_runtime),
) -> ChatResponse:
    response = await runtime.chat(
        prompt=req.prompt,
        system_prompt=req.system,
        max_turns=req.max_turns,
    )
    return ChatResponse(response=response)