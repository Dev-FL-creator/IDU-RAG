"""
Project Routes V2 - Project management endpoints with new schema.

Endpoints:
- GET /projects - List all projects for a user
- POST /projects - Create a new project
- GET /projects/{project_id} - Get project details
- PUT /projects/{project_id} - Update project
- DELETE /projects/{project_id} - Delete project (soft delete)
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_client import projects_collection, conversations_collection

router = APIRouter()


def generate_project_id() -> str:
    """Generate a unique project ID."""
    return f"proj_{uuid.uuid4().hex[:16]}"


# =============================================================================
# Project Routes
# =============================================================================

@router.get("/projects")
async def list_projects(user_id: str = Query(..., description="User ID")):
    """
    List all projects for a user.

    Query params:
    - user_id: User ID (required)

    Response:
    {
        "status": "ok",
        "projects": [...],
        "total": 5
    }
    """
    print(f"[Projects] Listing projects for user: {user_id}")
    if not user_id:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id is required"
        })

    # Get all projects for user, sorted by sort_order
    projects = list(projects_collection.find(
        {"user_id": user_id, "archived_at": None},
        {"_id": 0}  # Exclude MongoDB _id
    ).sort("sort_order", 1))
    print(f"[Projects] Found {len(projects)} projects")

    # Get conversation counts for each project
    for project in projects:
        count = conversations_collection.count_documents({
            "user_id": user_id,
            "project_id": project["id"],
            "is_archived": False
        })
        project["conversation_count"] = count
        # Convert datetime to ISO string
        if isinstance(project.get("created_at"), datetime):
            project["created_at"] = project["created_at"].isoformat()
        if isinstance(project.get("updated_at"), datetime):
            project["updated_at"] = project["updated_at"].isoformat()

    # Also count ungrouped conversations (project_id is None)
    ungrouped_count = conversations_collection.count_documents({
        "user_id": user_id,
        "project_id": None,
        "is_archived": False
    })

    return {
        "status": "ok",
        "projects": projects,
        "total": len(projects),
        "ungrouped_count": ungrouped_count
    }


@router.post("/projects")
async def create_project(request: Request):
    """
    Create a new project.

    Request body:
    {
        "user_id": "usr_xxx",
        "name": "My Project",
        "description": "Project description" (optional),
        "icon": "folder" (optional),
        "color": "#4A90D9" (optional)
    }

    Response:
    {
        "status": "ok",
        "message": "Project created successfully",
        "project": { ... }
    }
    """
    try:
        data = await request.json()
        print(f"[Projects] Creating project with data: {data}")
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    user_id = data.get("user_id")
    name = data.get("name", "").strip()
    description = data.get("description", "").strip() or None
    icon = data.get("icon")
    color = data.get("color")

    # Validate
    if not user_id:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "user_id is required",
            "field": "user_id"
        })

    if not name:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Project name is required",
            "field": "name"
        })

    if len(name) > 100:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Project name must be 100 characters or less",
            "field": "name"
        })

    # Get max sort_order for user's projects
    max_sort = projects_collection.find_one(
        {"user_id": user_id},
        sort=[("sort_order", -1)]
    )
    next_sort_order = (max_sort.get("sort_order", 0) + 1) if max_sort else 1

    # Create project
    now = datetime.utcnow()
    project = {
        "id": generate_project_id(),
        "user_id": user_id,
        "name": name,
        "description": description,
        "icon": icon,
        "color": color,
        "is_default": False,
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
        "sort_order": next_sort_order
    }

    projects_collection.insert_one(project)

    # Return without _id
    project.pop("_id", None)
    project["created_at"] = now.isoformat()
    project["updated_at"] = now.isoformat()
    project["conversation_count"] = 0

    return {
        "status": "ok",
        "message": "Project created successfully",
        "project": project
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str, user_id: str = Query(...)):
    """
    Get project details.

    Response:
    {
        "status": "ok",
        "project": { ... }
    }
    """
    project = projects_collection.find_one(
        {"id": project_id, "user_id": user_id},
        {"_id": 0}
    )

    if not project:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Project not found"
        })

    # Get conversation count
    count = conversations_collection.count_documents({
        "project_id": project_id,
        "is_archived": False
    })
    project["conversation_count"] = count

    # Convert datetime
    if isinstance(project.get("created_at"), datetime):
        project["created_at"] = project["created_at"].isoformat()
    if isinstance(project.get("updated_at"), datetime):
        project["updated_at"] = project["updated_at"].isoformat()

    return {
        "status": "ok",
        "project": project
    }


@router.put("/projects/{project_id}")
async def update_project(project_id: str, request: Request):
    """
    Update a project.

    Request body:
    {
        "user_id": "usr_xxx",
        "name": "New Name" (optional),
        "description": "New description" (optional),
        "icon": "new-icon" (optional),
        "color": "#FF0000" (optional),
        "sort_order": 2 (optional)
    }

    Response:
    {
        "status": "ok",
        "message": "Project updated successfully",
        "project": { ... }
    }
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

    # Check project exists
    project = projects_collection.find_one({"id": project_id, "user_id": user_id})
    if not project:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Project not found"
        })

    # Cannot update default project name
    if project.get("is_default") and "name" in data:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Cannot rename default project"
        })

    # Build update
    update_fields = {"updated_at": datetime.utcnow()}

    if "name" in data and data["name"]:
        name = data["name"].strip()
        if len(name) > 100:
            return JSONResponse(status_code=400, content={
                "status": "error",
                "message": "Project name must be 100 characters or less"
            })
        update_fields["name"] = name

    if "description" in data:
        update_fields["description"] = data["description"].strip() if data["description"] else None

    if "icon" in data:
        update_fields["icon"] = data["icon"]

    if "color" in data:
        update_fields["color"] = data["color"]

    if "sort_order" in data:
        update_fields["sort_order"] = data["sort_order"]

    # Update
    projects_collection.update_one(
        {"id": project_id},
        {"$set": update_fields}
    )

    # Get updated project
    updated = projects_collection.find_one({"id": project_id}, {"_id": 0})
    if isinstance(updated.get("created_at"), datetime):
        updated["created_at"] = updated["created_at"].isoformat()
    if isinstance(updated.get("updated_at"), datetime):
        updated["updated_at"] = updated["updated_at"].isoformat()

    return {
        "status": "ok",
        "message": "Project updated successfully",
        "project": updated
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user_id: str = Query(...)):
    """
    Delete a project (soft delete - archives it).
    Conversations in this project will be moved to ungrouped.

    Response:
    {
        "status": "ok",
        "message": "Project deleted successfully",
        "conversations_moved": 5
    }
    """
    # Check project exists
    project = projects_collection.find_one({"id": project_id, "user_id": user_id})
    if not project:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "Project not found"
        })

    # Cannot delete default project
    if project.get("is_default"):
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Cannot delete default project"
        })

    # Move all conversations to ungrouped (set project_id to None)
    result = conversations_collection.update_many(
        {"project_id": project_id, "user_id": user_id},
        {"$set": {"project_id": None, "updated_at": datetime.utcnow()}}
    )

    # Soft delete project
    projects_collection.update_one(
        {"id": project_id},
        {"$set": {"archived_at": datetime.utcnow()}}
    )

    return {
        "status": "ok",
        "message": "Project deleted successfully",
        "project_id": project_id,
        "conversations_moved": result.modified_count
    }
