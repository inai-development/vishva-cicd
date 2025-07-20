from fastapi import APIRouter, Request, HTTPException
from inai_project.app.history.history_manager import HistoryManager
from inai_project.app.history.history_schemas import ConversationCreate, MessageCreate
from fastapi.responses import JSONResponse

router = APIRouter()

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

@router.get("/conversation/{username}")
async def get_user_conversations(username: str, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations(username=username)
    return conversations

@router.get("/messages/{conversation_id}")
async def get_messages(conversation_id: str, request: Request):
    history_manager: HistoryManager = request.app.state.history_manager
    messages = await history_manager.get_conversation_messages(conversation_id=conversation_id)
    return messages
