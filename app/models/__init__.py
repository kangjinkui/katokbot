"""
Pydantic Models for KaTokBot API
"""

from .chat_models import (
    # User Models
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    # Session Models
    ChatSessionBase,
    ChatSessionCreate,
    ChatSessionResponse,
    # Message Models
    MessageType,
    MessageBase,
    MessageCreate,
    MessageResponse,
    # Chat Request/Response
    ChatRequest,
    ChatResponse,
    ChatHistoryRequest,
    ChatHistoryResponse,
    # Statistics Models
    UserStatistics,
    DailyStatistics,
    # Error & Health
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    # User Models
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    # Session Models
    "ChatSessionBase",
    "ChatSessionCreate",
    "ChatSessionResponse",
    # Message Models
    "MessageType",
    "MessageBase",
    "MessageCreate",
    "MessageResponse",
    # Chat Request/Response
    "ChatRequest",
    "ChatResponse",
    "ChatHistoryRequest",
    "ChatHistoryResponse",
    # Statistics
    "UserStatistics",
    "DailyStatistics",
    # Error & Health
    "ErrorResponse",
    "HealthResponse",
]
