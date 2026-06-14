from __future__ import annotations

from pydantic import BaseModel, Field, validator


class ChatHistoryMessage(BaseModel):
    role: str
    content: str = Field(..., min_length=1, max_length=4000)

    @validator("role")
    @classmethod
    def validate_role(cls, role: str) -> str:
        cleaned = role.strip().lower()
        if cleaned not in {"user", "assistant"}:
            raise ValueError("History role must be user or assistant.")
        return cleaned

    @validator("content")
    @classmethod
    def validate_content(cls, content: str) -> str:
        return content.strip()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list, max_length=12)
    conversation_id: int | None = None

    @validator("message")
    @classmethod
    def validate_message(cls, message: str) -> str:
        cleaned = message.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty.")
        return cleaned


class ChatResponse(BaseModel):
    answer: str
    model: str
    conversation_id: int | None = None
