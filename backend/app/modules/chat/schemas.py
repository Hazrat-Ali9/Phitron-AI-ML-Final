from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

MAX_HISTORY = 20


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[str, StringConstraints(max_length=8000)]


class ChatRequest(BaseModel):
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
    history: list[ChatTurn] = Field(
        default_factory=list,
        max_length=MAX_HISTORY,
        description="Previous turns, oldest first (the server keeps no chat state)",
    )


class ToolCallOut(BaseModel):
    name: str
    arguments: dict[str, Any]


class SourceOut(BaseModel):
    title: str
    snippet: str
    score: float


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    sources: list[SourceOut] = Field(default_factory=list)
