# src/api/routers/__init__.py
"""
Routers Package for Phase 3.0 API.
"""

from src.api.routers.health import router as health_router
from src.api.routers.auth import router as auth_router
from src.api.routers.sessions import router as sessions_router
from src.api.routers.turns import router as turns_router

__all__ = [
    "health_router",
    "auth_router",
    "sessions_router",
    "turns_router",
]
