from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MessageCreate(BaseModel):
    conversation_id: str
    role: str
    content: str


class ConversationCreate(BaseModel):
    username: str
    title: str
    mode: str


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime
    audio_url: Optional[str]


class ConversationResponse(BaseModel):
    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    is_archived: bool