"""
Pydantic schemas for IDU-RAG Backend API.

These schemas define the data models for:
- Users: Authentication and user management
- Projects: Project/folder organization
- Conversations: Chat conversations
- Messages: Individual chat messages
"""

from .user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserResponse,
    UserInDB
)

from .project import (
    ProjectBase,
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectInDB
)

from .conversation import (
    ConversationBase,
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationInDB
)

from .message import (
    MessageBase,
    MessageCreate,
    MessageResponse,
    MessageInDB
)

__all__ = [
    # User schemas
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "UserInDB",
    # Project schemas
    "ProjectBase",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectInDB",
    # Conversation schemas
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationInDB",
    # Message schemas
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    "MessageInDB",
]
