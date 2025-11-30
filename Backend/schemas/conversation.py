"""
Conversation Pydantic schemas for chat conversation management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ConversationBase(BaseModel):
    """Base conversation schema with common fields."""
    title: str = Field(default="New Conversation", max_length=200)


class ConversationCreate(BaseModel):
    """Schema for creating a new conversation."""
    user_id: str
    project_id: Optional[str] = None
    title: Optional[str] = "New Conversation"


class ConversationUpdate(BaseModel):
    """Schema for updating a conversation."""
    title: Optional[str] = Field(None, max_length=200)
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class ConversationMove(BaseModel):
    """Schema for moving a conversation to a different project."""
    project_id: Optional[str] = None  # None means ungrouped


class ConversationResponse(ConversationBase):
    """Schema for conversation response."""
    id: str
    user_id: str
    project_id: Optional[str] = None
    is_pinned: bool = False
    is_archived: bool = False
    message_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ConversationInDB(ConversationBase):
    """Schema for conversation stored in database."""
    id: str
    user_id: str
    project_id: Optional[str] = None
    is_pinned: bool = False
    is_archived: bool = False
    message_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
