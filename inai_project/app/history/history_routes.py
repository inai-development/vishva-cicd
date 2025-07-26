from fastapi import APIRouter, Request, HTTPException
from inai_project.app.history.history_manager import HistoryManager
from inai_project.app.history.history_schemas import ConversationCreate, MessageCreate
from pydantic import BaseModel

router = APIRouter()

# ------------------ Schemas ------------------

class NewChatRequest(BaseModel):
    username: str
    mode: str
    title: str = "New Conversation"

class SetActiveConversationRequest(BaseModel):
    username: str
    conversation_id: str

class UpdateTitleRequest(BaseModel):
    username: str
    conversation_id: str
    new_title: str

# ------------------ Routes ------------------

@router.post("/new-chat")
async def create_new_chat(request_data: NewChatRequest, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    conversation_id = await history_manager.create_new_conversation(
        user_id=request_data.username,
        mode=request_data.mode,
        title=request_data.title
    )
    return {
        "conversation_id": conversation_id,
        "message": "New chat created successfully",
        "status": "success"
    }

@router.post("/set-active")
async def set_active_conversation(request_data: SetActiveConversationRequest, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.set_active_conversation(
        user_id=request_data.username,
        conversation_id=request_data.conversation_id
    )
    return {
        "message": "Active conversation updated",
        "conversation_id": request_data.conversation_id,
        "status": "success"
    }

@router.get("/conversations/{username}")
async def get_user_conversations(username: str, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations_with_preview(username=username)
    return {
        "conversations": conversations,
        "total": len(conversations),
        "status": "success"
    }

@router.delete("/conversation/{conversation_id}")
async def archive_conversation(conversation_id: str, username: str, request: Request):
    if not username:
        raise HTTPException(status_code=400, detail="Username required")
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.archive_conversation(
        conversation_id=conversation_id,
        user_id=username
    )
    return {
        "message": "Conversation archived successfully",
        "conversation_id": conversation_id,
        "status": "success"
    }

@router.put("/conversation/title")
async def update_conversation_title(request_data: UpdateTitleRequest, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.update_conversation_title(
        conversation_id=request_data.conversation_id,
        new_title=request_data.new_title,
        user_id=request_data.username
    )
    return {
        "message": "Title updated successfully",
        "new_title": request_data.new_title,
        "status": "success"
    }

@router.post("/conversation/create")
async def create_conversation(conversation: ConversationCreate, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    conversation_id = await history_manager.create_conversation(
        username=conversation.username,
        title=conversation.title,
        mode=conversation.mode
    )
    return {"conversation_id": conversation_id}

@router.post("/message/save")
async def save_message(message: MessageCreate, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.save_message(
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content
    )
    return {"status": "saved"}

@router.get("/conversations/user/{user_id}/{mode}")
async def get_conversations_by_mode(user_id: str, mode: str, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations_by_mode(user_id=user_id, mode=mode)
    return {
        "conversations": conversations,
        "total": len(conversations),
        "status": "success"
    }



@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    messages = await history_manager.get_conversation_messages(conversation_id=conversation_id)
    return {
        "messages": messages,
        "conversation_id": conversation_id,
        "total": len(messages)
    }