from datetime import datetime
from pydantic import BaseModel


class SessionCreate(BaseModel):
    name: str


class SessionRead(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionListItem(SessionRead):
    message_count: int = 0
