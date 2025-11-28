
from fastapi import APIRouter, Request
from mongodb_client import chat_collection
from fastapi.responses import JSONResponse

router = APIRouter()


# 保存聊天记录，支持会话元数据
@router.post("/chat/save")
async def save_chat(request: Request):
    data = await request.json()
    # 支持会话元数据：conversation_id, project_id, title
    chat_collection.insert_one(data)
    return {"status": "ok"}


# 获取某用户所有会话（分组返回）
@router.get("/chat/history")
async def get_chat_history(user_id: str):
    # 聚合分组，返回每个conversation_id的最新一条消息（用于会话列表）
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$sort": {"timestamp": -1}},
        {"$group": {
            "_id": "$conversation_id",
            "title": {"$first": "$title"},
            "project_id": {"$first": "$project_id"},
            "last_message": {"$first": "$content"},
            "timestamp": {"$first": "$timestamp"}
        }}
    ]
    conversations = list(chat_collection.aggregate(pipeline))
    for conv in conversations:
        conv["conversation_id"] = conv.pop("_id")
    return conversations

# 获取某会话所有消息
@router.get("/chat/conversation")
async def get_conversation(conversation_id: str):
    chats = list(chat_collection.find({"conversation_id": conversation_id}).sort("timestamp", 1))
    for chat in chats:
        chat["_id"] = str(chat["_id"])
    return chats

# 重命名会话
@router.post("/chat/rename")
async def rename_conversation(request: Request):
    data = await request.json()
    conversation_id = data.get("conversation_id")
    new_title = data.get("new_title")
    if not conversation_id or not new_title:
        return JSONResponse(status_code=400, content={"error": "Missing conversation_id or new_title"})
    chat_collection.update_many({"conversation_id": conversation_id}, {"$set": {"title": new_title}})
    return {"status": "ok"}

# 删除会话（连带所有消息）
@router.post("/chat/delete")
async def delete_conversation(request: Request):
    data = await request.json()
    conversation_id = data.get("conversation_id")
    if not conversation_id:
        return JSONResponse(status_code=400, content={"error": "Missing conversation_id"})
    chat_collection.delete_many({"conversation_id": conversation_id})
    return {"status": "ok"}

# 移动会话到Project
@router.post("/chat/move")
async def move_conversation(request: Request):
    data = await request.json()
    conversation_id = data.get("conversation_id")
    project_id = data.get("project_id")
    print(f"[MoveConversation] conversation_id: {conversation_id}, project_id: {project_id}")
    if not conversation_id or not project_id:
        print("[MoveConversation] 参数缺失，操作终止")
        return JSONResponse(status_code=400, content={"error": "Missing conversation_id or project_id"})
    result = chat_collection.update_many({"conversation_id": conversation_id}, {"$set": {"project_id": project_id}})
    print(f"[MoveConversation] update matched: {result.matched_count}, modified: {result.modified_count}")
    return {"status": "ok"}

# 获取所有Project及其会话
@router.get("/chat/projects")
async def get_projects(user_id: str):
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$project_id", "conversations": {"$addToSet": "$conversation_id"}}}
    ]
    projects = list(chat_collection.aggregate(pipeline))
    for proj in projects:
        proj["project_id"] = proj.pop("_id")
    return projects
