"""
Project Pydantic schemas for project/folder management.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectBase(BaseModel):
    """Base project schema with common fields."""
    name: str = Field(..., max_length=100, description="Project name")
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""
    user_id: str


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class ProjectResponse(ProjectBase):
    """Schema for project response."""
    id: str
    user_id: str
    is_default: bool = False
    created_at: str
    updated_at: str
    archived_at: Optional[str] = None
    sort_order: int = 0
    conversation_count: int = 0

    class Config:
        from_attributes = True


class ProjectInDB(ProjectBase):
    """Schema for project stored in database."""
    id: str
    user_id: str
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None
    sort_order: int = 0

    class Config:
        from_attributes = True
