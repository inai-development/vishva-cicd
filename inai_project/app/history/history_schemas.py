from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MessageCreate(BaseModel):
    conversation_id: str
    role: str
    content: str


class ConversationCreate(BaseModel):
    user_id: str
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
    first_message: str  # Changed from Optional to required
    preview: str  # This will now use first_message
    message_count: int = 0


class ConversationWithMessages(BaseModel):
    conversation: ConversationResponse
    messages: List[MessageResponse]
    total_messages: int


class ModeResponse(BaseModel):
    mode: str
    display_name: str
    conversation_count: int
    last_updated: Optional[datetime]


class HistoryFlowResponse(BaseModel):
    """Response for history flow endpoints"""
    status: str
    message: Optional[str] = None


class ModesListResponse(HistoryFlowResponse):
    modes: List[ModeResponse]
    total: int


class ConversationsListResponse(HistoryFlowResponse):
    conversations: List[ConversationResponse]
    mode: str
    total: int


class ConversationDetailResponse(HistoryFlowResponse):
    conversation: ConversationResponse
    messages: List[MessageResponse]
    conversation_id: str
    total_messages: int


# Request schemas for history flow
class SelectModeRequest(BaseModel):
    user_id: str
    mode: str


class SelectConversationRequest(BaseModel):
    user_id: str
    conversation_id: str


class CreateNewConversationFromHistory(BaseModel):
    user_id: str
    mode: str
    title: str = "New Conversation"


# New schemas for title management
class AutoUpdateTitleRequest(BaseModel):
    user_id: str
    conversation_id: str


class TitleUpdateResponse(BaseModel):
    message: str
    old_title: str
    new_title: str
    status: str


class BulkTitleUpdateResponse(BaseModel):
    message: str
    updated_conversations: List[dict]
    status: str


class TitleRegenerationRequest(BaseModel):
    user_id: str
    force_update: bool = False  # If True, updates even non-default titles


# Enhanced conversation preview schema
class ConversationPreview(BaseModel):
    id: str
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime
    preview: str  # First user message for display
    message_count: int
    has_audio: bool = False  # If conversation contains audio messages
    last_activity: str  # Human readable time like "2 hours ago"


class EnhancedConversationsListResponse(HistoryFlowResponse):
    conversations: List[ConversationPreview]
    mode: str
    total: int
    page: Optional[int] = None
    per_page: Optional[int] = None