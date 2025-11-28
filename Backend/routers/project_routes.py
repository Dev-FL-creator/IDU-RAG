from fastapi import APIRouter, Request
from mongodb_client import chat_collection
from fastapi.responses import JSONResponse

router = APIRouter()

# 新建 Project
@router.post("/chat/project/new")
async def create_project(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    project_id = data.get("project_id")
    name = data.get("name")
    if not user_id or not project_id or not name:
        return JSONResponse(status_code=400, content={"error": "Missing user_id, project_id or name"})
    # Project 只存一条元数据，实际会话数据仍在 chat_collection
    chat_collection.insert_one({
        "user_id": user_id,
        "project_id": project_id,
        "project_name": name,
        "is_project_meta": True
    })
    return {"status": "ok"}

# 重命名 Project
@router.post("/chat/project/rename")
async def rename_project(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    project_id = data.get("project_id")
    new_name = data.get("new_name")
    if not user_id or not project_id or not new_name:
        return JSONResponse(status_code=400, content={"error": "Missing user_id, project_id or new_name"})
    chat_collection.update_many({"user_id": user_id, "project_id": project_id, "is_project_meta": True}, {"$set": {"project_name": new_name}})
    return {"status": "ok"}

# 删除 Project（不删除会话，只删除元数据）
@router.post("/chat/project/delete")
async def delete_project(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    project_id = data.get("project_id")
    if not user_id or not project_id:
        return JSONResponse(status_code=400, content={"error": "Missing user_id or project_id"})
    chat_collection.delete_many({"user_id": user_id, "project_id": project_id, "is_project_meta": True})
    return {"status": "ok"}

# 获取所有 Project 元数据
@router.get("/chat/project/meta")
async def get_project_meta(user_id: str):
    projects = list(chat_collection.find({"user_id": user_id, "is_project_meta": True}))
    for proj in projects:
        proj["project_id"] = proj.get("project_id")
        proj["name"] = proj.get("project_name")
        proj["_id"] = str(proj["_id"])
    return projects
