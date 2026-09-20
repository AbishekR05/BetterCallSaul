# src/api/routers/health.py
"""
Health & Readiness Endpoints (§5, §10).
"""

from fastapi import APIRouter, Depends, status
from src.api.dependencies import get_session_store
from src.conversation.session_store import SessionStore

router = APIRouter(tags=["Health"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe - confirms API process is running (§5)."""
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(session_store: SessionStore = Depends(get_session_store)):
    """Readiness probe - verifies session store connectivity (§5, §10)."""
    try:
        if hasattr(session_store, "_get_connection"):
            conn = session_store._get_connection()
            conn.close()
        elif hasattr(session_store, "_store"):
            _ = len(session_store._store)
        return {"status": "ready"}
    except Exception as e:
        raise ConnectionError(f"Database connection unavailable: {e}")
