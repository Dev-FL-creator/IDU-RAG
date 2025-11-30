"""
User Routes - User authentication endpoints.

Endpoints:
- POST /auth/register - Register a new user
- POST /auth/login - Login user
- GET /auth/user/{user_id} - Get user info
- GET /auth/check-email - Check if email exists
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse
from datetime import datetime
import uuid
import hashlib
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_client import users_collection, projects_collection

router = APIRouter()


def generate_user_id() -> str:
    """Generate a unique user ID."""
    return f"usr_{uuid.uuid4().hex[:16]}"


def hash_password(password: str) -> str:
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


# =============================================================================
# Auth Routes
# =============================================================================

@router.post("/auth/register")
async def register(request: Request):
    """
    Register a new user.

    Request body:
    {
        "email": "user@example.com",
        "password": "password123",
        "username": "optional_username"
    }
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    username = data.get("username", "").strip() or None

    # Validate
    if not email or "@" not in email:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Valid email is required",
            "field": "email"
        })

    if len(password) < 6:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Password must be at least 6 characters",
            "field": "password"
        })

    # Check if email exists
    existing = users_collection.find_one({"email": email})
    if existing:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Email already registered",
            "field": "email"
        })

    # Create user
    now = datetime.utcnow()
    user = {
        "id": generate_user_id(),
        "email": email,
        "password_hash": hash_password(password),
        "username": username,
        "created_at": now,
        "updated_at": now,
        "is_active": True
    }

    users_collection.insert_one(user)

    # Create default project for user
    default_project = {
        "id": f"proj_{uuid.uuid4().hex[:16]}",
        "user_id": user["id"],
        "name": "Ungrouped",
        "description": "Default project for ungrouped conversations",
        "icon": None,
        "color": None,
        "is_default": True,
        "created_at": now,
        "updated_at": now,
        "archived_at": None,
        "sort_order": 0
    }
    projects_collection.insert_one(default_project)

    # Return user (without password_hash)
    return {
        "status": "ok",
        "message": "User registered successfully",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user["username"],
            "created_at": now.isoformat(),
            "is_active": True
        }
    }


@router.post("/auth/login")
async def login(request: Request):
    """
    Login user.

    Request body:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    """
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Invalid JSON body"
        })

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Email and password are required"
        })

    # Find user
    user = users_collection.find_one({"email": email})
    if not user:
        return JSONResponse(status_code=401, content={
            "status": "error",
            "message": "Invalid email or password"
        })

    # Check password
    if user["password_hash"] != hash_password(password):
        return JSONResponse(status_code=401, content={
            "status": "error",
            "message": "Invalid email or password"
        })

    # Check if active
    if not user.get("is_active", True):
        return JSONResponse(status_code=401, content={
            "status": "error",
            "message": "Account is deactivated"
        })

    # Return user (without password_hash)
    created_at = user.get("created_at")
    if isinstance(created_at, datetime):
        created_at = created_at.isoformat()

    return {
        "status": "ok",
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "username": user.get("username"),
            "created_at": created_at,
            "is_active": user.get("is_active", True)
        }
    }


@router.get("/auth/user/{user_id}")
async def get_user(user_id: str):
    """
    Get user info by ID.
    """
    user = users_collection.find_one({"id": user_id}, {"password_hash": 0, "_id": 0})
    if not user:
        return JSONResponse(status_code=404, content={
            "status": "error",
            "message": "User not found"
        })

    # Convert datetime
    if isinstance(user.get("created_at"), datetime):
        user["created_at"] = user["created_at"].isoformat()
    if isinstance(user.get("updated_at"), datetime):
        user["updated_at"] = user["updated_at"].isoformat()

    return {
        "status": "ok",
        "user": user
    }


@router.get("/auth/check-email")
async def check_email(email: str = Query(...)):
    """
    Check if email is already registered.
    """
    email = email.strip().lower()
    existing = users_collection.find_one({"email": email})
    return {"exists": existing is not None}
