from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    content: str


class MessageRead(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageMetadata(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class DoneEventData(BaseModel):
    message_id: str
    usage: Optional[UsageMetadata] = None
