from fastapi import APIRouter, Request, HTTPException, Query
from .history_manager import HistoryManager
from .history_schemas import ConversationCreate, MessageCreate
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

# ------------------ Schemas ------------------

class NewChatRequest(BaseModel):
    user_id: str
    mode: str
    title: str = "New Conversation"

class SetActiveConversationRequest(BaseModel):
    user_id: str
    conversation_id: str

class UpdateTitleRequest(BaseModel):
    user_id: str
    conversation_id: str
    new_title: str

class ModeSelectionRequest(BaseModel):
    user_id: str
    selected_mode: str

class AutoUpdateTitleRequest(BaseModel):
    user_id: str
    conversation_id: str

# ------------------ History Flow Routes ------------------

@router.get("/modes/{user_id}")
async def get_user_modes(user_id: str, request: Request):
    """Step 1: Get available modes for user when History is clicked"""
    history_manager: HistoryManager = request.app.state.history_manager
    modes_summary = await history_manager.get_user_modes_summary(user_id)
    
    # If no conversations exist, return default modes
    if not modes_summary:
        default_modes = [
            {"mode": "friend", "display_name": "Friend Mode", "conversation_count": 0, "last_updated": None},
            {"mode": "information", "display_name": "Information Mode", "conversation_count": 0, "last_updated": None},
            {"mode": "love", "display_name": "Love Mode", "conversation_count": 0, "last_updated": None},
            {"mode": "elder", "display_name": "Elder Mode", "conversation_count": 0, "last_updated": None}
        ]
        return {
            "modes": default_modes,
            "total": len(default_modes),
            "status": "success",
            "message": "Default modes returned - no conversations found"
        }
    
    return {
        "modes": modes_summary,
        "total": len(modes_summary),
        "status": "success"
    }

@router.get("/conversations/{user_id}/{mode}")
async def get_conversations_by_mode(user_id: str, mode: str, request: Request):
    """Step 2: Get conversations for selected mode"""
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations_by_mode(user_id, mode)
    
    return {
        "conversations": conversations,
        "mode": mode,
        "total": len(conversations),
        "status": "success"
    }

@router.get("/conversation/{conversation_id}")
async def get_conversation_messages(conversation_id: str, user_id: str, request: Request):
    """Step 3: Get messages for selected conversation"""
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    
    history_manager: HistoryManager = request.app.state.history_manager
    
    # First verify conversation belongs to user
    conversation_details = await history_manager.get_conversation_details(conversation_id, user_id)
    if not conversation_details:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get messages
    messages = await history_manager.get_conversation_messages(conversation_id)
    
    return {
        "conversation": conversation_details,
        "messages": messages,
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "status": "success"
    }

@router.post("/history/set-active")
async def set_active_conversation_from_history(request_data: SetActiveConversationRequest, request: Request):
    """Set active conversation when user selects from history"""
    history_manager: HistoryManager = request.app.state.history_manager
    
    try:
        await history_manager.set_active_conversation(
            user_id=request_data.user_id,
            conversation_id=request_data.conversation_id
        )
        return {
            "message": "Active conversation set from history",
            "conversation_id": request_data.conversation_id,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ------------------ New Title Management Routes ------------------

@router.post("/conversation/auto-update-title")
async def auto_update_conversation_title(request_data: AutoUpdateTitleRequest, request: Request):
    """Auto-update conversation title based on first assistant response"""
    history_manager: HistoryManager = request.app.state.history_manager
    
    try:
        # Get first assistant response from the conversation
        async with history_manager.pool.acquire() as conn:
            # Verify conversation belongs to user
            conversation = await conn.fetchrow("""
                SELECT id, title FROM conversations 
                WHERE id = $1 AND user_id = $2 AND is_archived = false
            """, request_data.conversation_id, request_data.user_id)
            
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            # Get first assistant response
            first_assistant_response = await conn.fetchval("""
                SELECT content FROM messages 
                WHERE conversation_id = $1 AND role = 'assistant'
                ORDER BY created_at ASC 
                LIMIT 1
            """, request_data.conversation_id)
            
            if first_assistant_response:
                # Generate new title from assistant response
                new_title = history_manager.generate_smart_title(first_assistant_response, "assistant")
                
                # Update the title
                await history_manager.update_conversation_title(
                    conversation_id=request_data.conversation_id,
                    new_title=new_title,
                    user_id=request_data.user_id
                )
                
                return {
                    "message": "Title updated successfully from assistant response",
                    "old_title": conversation['title'],
                    "new_title": new_title,
                    "status": "success"
                }
            else:
                raise HTTPException(status_code=400, detail="No assistant response found to generate title")
                
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conversation/regenerate-titles")
async def regenerate_all_conversation_titles(user_id: str, request: Request):
    """Regenerate titles for all conversations with default titles"""
    history_manager: HistoryManager = request.app.state.history_manager
    
    try:
        updated_conversations = []
        
        async with history_manager.pool.acquire() as conn:
            # Get all conversations with default titles
            conversations = await conn.fetch("""
                SELECT id, title FROM conversations 
                WHERE user_id = $1 AND title = 'New Conversation' AND is_archived = false
            """, user_id)
            
            for conv in conversations:
                # Get first assistant response for each conversation
                first_response = await conn.fetchval("""
                    SELECT content FROM messages 
                    WHERE conversation_id = $1 AND role = 'assistant'
                    ORDER BY created_at ASC 
                    LIMIT 1
                """, conv['id'])
                
                if first_response:
                    new_title = history_manager.generate_smart_title(first_response, "assistant")
                    
                    if new_title != "New Conversation":
                        await history_manager.update_conversation_title(
                            conversation_id=conv['id'],
                            new_title=new_title,
                            user_id=user_id
                        )
                        updated_conversations.append({
                            "conversation_id": conv['id'],
                            "old_title": conv['title'],
                            "new_title": new_title
                        })
        
        return {
            "message": f"Updated {len(updated_conversations)} conversation titles",
            "updated_conversations": updated_conversations,
            "status": "success"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ------------------ Existing Routes (Updated for better organization) ------------------

@router.post("/new-chat")
async def create_new_chat(request_data: NewChatRequest, request: Request):
    """Create new conversation"""
    history_manager: HistoryManager = request.app.state.history_manager
    conversation_id = await history_manager.create_new_conversation(
        user_id=request_data.user_id,
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
    """Set active conversation (general purpose)"""
    history_manager: HistoryManager = request.app.state.history_manager
    
    try:
        await history_manager.set_active_conversation(
            user_id=request_data.user_id,
            conversation_id=request_data.conversation_id
        )
        return {
            "message": "Active conversation updated",
            "conversation_id": request_data.conversation_id,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/conversations/{user_id}")
async def get_user_conversations(user_id: str, request: Request):
    """Get all conversations for user (used for sidebar or general listing)"""
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations_with_preview(user_id=user_id)
    return {
        "conversations": conversations,
        "total": len(conversations),
        "status": "success"
    }

@router.delete("/conversation/{conversation_id}")
async def archive_conversation(conversation_id: str, user_id: str, request: Request):
    """Archive/Delete conversation"""
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID required")
    
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.archive_conversation(
        conversation_id=conversation_id,
        user_id=user_id
    )
    return {
        "message": "Conversation archived successfully",
        "conversation_id": conversation_id,
        "status": "success"
    }

@router.put("/conversation/title")
async def update_conversation_title(request_data: UpdateTitleRequest, request: Request):
    """Update conversation title"""
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.update_conversation_title(
        conversation_id=request_data.conversation_id,
        new_title=request_data.new_title,
        user_id=request_data.user_id
    )
    return {
        "message": "Title updated successfully",
        "new_title": request_data.new_title,
        "status": "success"
    }

@router.post("/conversation/create")
async def create_conversation(conversation: ConversationCreate, request: Request):
    """Create conversation (alternative endpoint)"""
    history_manager: HistoryManager = request.app.state.history_manager
    conversation_id = await history_manager.create_new_conversation(
        user_id=conversation.user_id,
        title=conversation.title,
        mode=conversation.mode
    )
    return {
        "conversation_id": conversation_id,
        "status": "success"
    }

@router.post("/message/save")
async def save_message(message: MessageCreate, request: Request):
    """Save message to conversation"""
    history_manager: HistoryManager = request.app.state.history_manager
    await history_manager.save_message(
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content
    )
    return {"status": "saved"}

# Legacy route - keeping for backward compatibility
@router.get("/conversations/user/{user_id}/{mode}")
async def get_conversations_by_mode_legacy(user_id: str, mode: str, request: Request):
    """Legacy endpoint - use /history/conversations/{user_id}/{mode} instead"""
    history_manager: HistoryManager = request.app.state.history_manager
    conversations = await history_manager.get_user_conversations_by_mode(user_id=user_id, mode=mode)
    return {
        "conversations": conversations,
        "total": len(conversations),
        "status": "success"
    }

# Legacy route - keeping for backward compatibility  
@router.get("/messages/{conversation_id}")
async def get_messages_legacy(conversation_id: str, user_id: str = Query(None), request: Request = None):
    """Legacy endpoint - use /history/conversation/{conversation_id} instead"""
    history_manager: HistoryManager = request.app.state.history_manager
    messages = await history_manager.get_conversation_messages(conversation_id=conversation_id)
    return {
        "messages": messages,
        "conversation_id": conversation_id,
        "total": len(messages)
    }