from fastapi import APIRouter, Request
from mongodb_client import chat_collection

router = APIRouter()

@router.post("/chat/save")
async def save_chat(request: Request):
    data = await request.json()
    chat_collection.insert_one(data)
    return {"status": "ok"}

@router.get("/chat/history")
async def get_chat_history(user_id: str):
    chats = list(chat_collection.find({"user_id": user_id}))
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return chats
