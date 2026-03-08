from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system: str | None = None
    max_turns: int = Field(default=20, ge=1, le=100)


class ChatResponse(BaseModel):
    response: str