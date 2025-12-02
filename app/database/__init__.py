"""
Database Connection and Repository Pattern
"""

from .connection import Database
from .repositories import UserRepository, SessionRepository, MessageRepository

# 전역 데이터베이스 인스턴스
db = Database()
user_repo = UserRepository(db)
session_repo = SessionRepository(db)
message_repo = MessageRepository(db)

__all__ = [
    "Database",
    "UserRepository",
    "SessionRepository",
    "MessageRepository",
    "db",
    "user_repo",
    "session_repo",
    "message_repo",
]
