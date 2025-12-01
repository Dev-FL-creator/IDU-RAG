"""
User Pydantic schemas for authentication and user management.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr
    username: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)."""
    id: str
    created_at: str
    is_active: bool = True

    class Config:
        from_attributes = True


class UserInDB(UserBase):
    """Schema for user stored in database."""
    id: str
    password_hash: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True
