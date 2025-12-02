"""
FastAPI Routers for KaTokBot API
"""

from .chat import chat_router
from .users import user_router
from .stats import stats_router
from .admin import admin_router
from .qa import qa_router
from .dashboard import dashboard_router

__all__ = [
    "chat_router",
    "user_router",
    "stats_router",
    "admin_router",
    "qa_router",
    "dashboard_router",
]
