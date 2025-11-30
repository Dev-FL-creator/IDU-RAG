"""
Message Pydantic schemas for chat message management.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageBase(BaseModel):
    """Base message schema with common fields."""
    role: MessageRole
    content: str


class MessageCreate(BaseModel):
    """Schema for creating a new message."""
    conversation_id: str
    role: MessageRole
    content: str
    sources: Optional[List[Any]] = None
    metadata: Optional[dict] = None


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    conversation_id: str
    sources: Optional[List[Any]] = None
    metadata: Optional[dict] = None
    created_at: str

    class Config:
        from_attributes = True


class MessageInDB(MessageBase):
    """Schema for message stored in database."""
    id: str
    conversation_id: str
    sources: Optional[List[Any]] = None
    metadata: Optional[dict] = None
    created_at: datetime

    class Config:
        from_attributes = True
