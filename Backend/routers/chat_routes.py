"""
Conversation Routes - Conversation and message management endpoints.

Endpoints:
- GET /conversations - List all conversations for a user
- POST /conversations - Create a new conversation
- GET /conversations/{conversation_id} - Get conversation with messages
- PUT /conversations/{conversation_id} - Update conversation
- DELETE /conversations/{conversation_id} - Delete conversation
- POST /conversations/{conversation_id}/move - Move conversation to project
- POST /conversations/{conversation_id}/messages - Add message to conversation
- POST /conversations/generate-title - Generate title using AI
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_client import conversations_collection, messages_collection, projects_collection
from openai import OpenAI as OpenAIPlatform

router = APIRouter()


def generate_conversation_id() -> str:
    """Generate a unique conversation ID."""
    return f"conv_{uuid.uuid4().hex[:16]}"


def generate_message_id() -> str:
    """Generate a unique message ID."""
    return f"msg_{uuid.uuid4().hex[:16]}"


# =============================================================================
# Conversation Routes
# =============================================================================

@router.get("/conversations")
async def list_conversations(
    user_id: str = Query(..., description="User ID"),
    project_id: str = Query(None, description="Filter by project ID")
):
    """
    List all conversations for a user, optionally filtered by project.
    """
    print(f"[Conversations] Listing conversations for user: {user_id}, project: {project_id}")

    query = {"user_id": user_id, "is_archived": False}
    if project_id:
        query["project_id"] = project_id

    conversations = list(conversations_collection.find(
        query,
        {"_id": 0}
    ).sort("updated_at", -1))

    # Add project name and last message preview
    for conv in conversations:
        # Get project name
        if conv.get("project_id"):
            project = projects_collection.find_one({"id": conv["project_id"]}, {"name": 1})
            conv["project_name"] = project["name"] if project else None
        else:
            conv["project_name"] = None

        # Get last message preview
        last_msg = messages_collection.find_one(
            {"conversation_id": conv["id"]},
            {"content": 1},
            sort=[("created_at", -1)]
        )
        conv["last_message_preview"] = last_msg["content"][:100] if last_msg else None

        # Convert datetime to ISO string
        for field in ["created_at", "updated_at", "last_message_at", "archived_at"]:
            if isinstance(conv.get(field), datetime):
                conv[field] = conv[field].isoformat()

    print(f"[Conversations] Found {len(conversations)} conversations")
    return {
        "status": "ok",
        "conversations": conversations,
        "total": len(conversations)
    }


@router.post("/conversations")
async def create_conversation(request: Request):
    """
    Create a new conversation.
    """
    try:
        data = await request.json()
        print(f"[Conversations] Creating conversation with data: {data}")
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    user_id = data.get("user_id")
    project_id = data.get("project_id")
    title = data.get("title", "New Conversation")

    if not user_id:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id is required"
        })

    now = datetime.utcnow()
    conversation = {
        "id": generate_conversation_id(),
        "user_id": user_id,
        "project_id": project_id,
        "title": title,
        "summary": None,
        "created_at": now,
        "updated_at": now,
        "last_message_at": None,
        "message_count": 0,
        "is_pinned": False,
        "is_archived": False,
        "archived_at": None,
        "metadata": None
    }

    conversations_collection.insert_one(conversation)

    # Return without _id
    conversation.pop("_id", None)
    conversation["created_at"] = now.isoformat()
    conversation["updated_at"] = now.isoformat()

    return {
        "status": "ok",
        "message": "Conversation created successfully",
        "conversation": conversation
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user_id: str = Query(...)):
    """
    Get conversation details with all messages.
    """
    conversation = conversations_collection.find_one(
        {"id": conversation_id, "user_id": user_id},
        {"_id": 0}
    )

    if not conversation:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Conversation not found"
        })

    # Get all messages
    messages = list(messages_collection.find(
        {"conversation_id": conversation_id},
        {"_id": 0}
    ).sort("created_at", 1))

    # Convert datetime fields
    for field in ["created_at", "updated_at", "last_message_at", "archived_at"]:
        if isinstance(conversation.get(field), datetime):
            conversation[field] = conversation[field].isoformat()

    for msg in messages:
        for field in ["created_at", "updated_at"]:
            if isinstance(msg.get(field), datetime):
                msg[field] = msg[field].isoformat()

    return {
        "status": "ok",
        "conversation": conversation,
        "messages": messages
    }


@router.put("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, request: Request):
    """
    Update a conversation (title, pinned status, etc.).
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    user_id = data.get("user_id")
    if not user_id:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id is required"
        })

    # Check conversation exists
    conversation = conversations_collection.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Conversation not found"
        })

    # Build update
    update_fields = {"updated_at": datetime.utcnow()}

    if "title" in data:
        update_fields["title"] = data["title"]

    if "is_pinned" in data:
        update_fields["is_pinned"] = data["is_pinned"]

    if "is_archived" in data:
        update_fields["is_archived"] = data["is_archived"]
        if data["is_archived"]:
            update_fields["archived_at"] = datetime.utcnow()

    # Update
    conversations_collection.update_one(
        {"id": conversation_id},
        {"$set": update_fields}
    )

    # Get updated conversation
    updated = conversations_collection.find_one({"id": conversation_id}, {"_id": 0})
    for field in ["created_at", "updated_at", "last_message_at", "archived_at"]:
        if isinstance(updated.get(field), datetime):
            updated[field] = updated[field].isoformat()

    return {
        "status": "ok",
        "message": "Conversation updated successfully",
        "conversation": updated
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, user_id: str = Query(...)):
    """
    Delete a conversation and all its messages.
    """
    # Check conversation exists
    conversation = conversations_collection.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Conversation not found"
        })

    # Delete all messages
    messages_collection.delete_many({"conversation_id": conversation_id})

    # Delete conversation
    conversations_collection.delete_one({"id": conversation_id})

    return {
        "status": "ok",
        "message": "Conversation deleted successfully",
        "conversation_id": conversation_id
    }


@router.post("/conversations/{conversation_id}/move")
async def move_conversation(conversation_id: str, request: Request):
    """
    Move a conversation to a different project.
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    user_id = data.get("user_id")
    new_project_id = data.get("project_id")  # Can be None for ungrouped

    if not user_id:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id is required"
        })

    # Check conversation exists
    conversation = conversations_collection.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Conversation not found"
        })

    old_project_id = conversation.get("project_id")

    # Get project names for response
    old_project_name = "Ungrouped"
    new_project_name = "Ungrouped"

    if old_project_id:
        old_project = projects_collection.find_one({"id": old_project_id})
        if old_project:
            old_project_name = old_project.get("name", "Unknown")

    if new_project_id:
        new_project = projects_collection.find_one({"id": new_project_id})
        if new_project:
            new_project_name = new_project.get("name", "Unknown")

    # Update conversation
    conversations_collection.update_one(
        {"id": conversation_id},
        {"$set": {"project_id": new_project_id, "updated_at": datetime.utcnow()}}
    )

    return {
        "status": "ok",
        "message": "Conversation moved successfully",
        "conversation_id": conversation_id,
        "old_project_id": old_project_id,
        "old_project_name": old_project_name,
        "new_project_id": new_project_id,
        "new_project_name": new_project_name
    }


@router.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, request: Request):
    """
    Add a message to a conversation.
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    user_id = data.get("user_id")
    role = data.get("role")
    content = data.get("content")

    if not all([user_id, role, content]):
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id, role, and content are required"
        })

    # Check conversation exists
    conversation = conversations_collection.find_one({"id": conversation_id, "user_id": user_id})
    if not conversation:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Conversation not found"
        })

    now = datetime.utcnow()
    message = {
        "id": generate_message_id(),
        "conversation_id": conversation_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "created_at": now,
        "updated_at": None,
        "is_edited": False,
        "metadata": data.get("metadata"),
        "model": data.get("model"),
        "feedback": None
    }

    messages_collection.insert_one(message)

    # Update conversation
    conversations_collection.update_one(
        {"id": conversation_id},
        {
            "$set": {"updated_at": now, "last_message_at": now},
            "$inc": {"message_count": 1}
        }
    )

    # Return without _id
    message.pop("_id", None)
    message["created_at"] = now.isoformat()

    return {
        "status": "ok",
        "message": "Message added successfully",
        "message_data": message
    }


@router.post("/conversations/generate-title")
async def generate_title(request: Request):
    """
    Generate a title for a conversation using AI.
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    conversation = data.get("conversation")
    if not conversation or not isinstance(conversation, str):
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "conversation content is required"
        })

    # Load config
    def load_config() -> dict:
        cfg_path = os.getenv("CONFIG_PATH") or os.path.join(os.path.dirname(__file__), "..", "config.json")
        cfg_path = os.path.abspath(cfg_path)
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)

    try:
        cfg = load_config()
        client = OpenAIPlatform(
            api_key=cfg.get("deepseek_api_key"),
            base_url=cfg.get("deepseek_base_url", "https://api.deepseek.com")
        )

        prompt = "Generate a concise and accurate title (no more than 10 words, English preferred) for the following conversation:\n\n" + conversation

        rsp = client.chat.completions.create(
            model=cfg.get("deepseek_chat_model", "deepseek-chat"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.3
        )

        title = rsp.choices[0].message.content.strip() if rsp.choices and rsp.choices[0].message.content else "AI Conversation"

        return {"status": "ok", "title": title}

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": f"Failed to generate title: {str(e)}"
        })
