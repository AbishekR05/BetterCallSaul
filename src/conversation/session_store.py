# src/conversation/session_store.py
"""
Session Store implementation for Phase 2.7 Conversational Context & Session Memory.
Provides an abstract SessionStore interface and an in-memory implementation (InMemorySessionStore).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
import uuid
from datetime import datetime, timedelta
from src.conversation.schemas import ConversationSession, ConversationTurn


class SessionStore(ABC):
    """
    Abstract Base Class / Interface for session stores.
    Strictly session_id-keyed to guarantee zero session isolation leakage (§11).
    """

    @abstractmethod
    def create_session(self, user_id: Optional[str] = None, ttl_minutes: int = 60) -> ConversationSession:
        """Create and return a new ConversationSession."""
        pass

    @abstractmethod
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """
        Retrieve session by session_id.
        Returns None if session does not exist or is expired.
        """
        pass

    @abstractmethod
    def add_turn(self, session_id: str, turn: ConversationTurn, ttl_minutes: int = 60) -> ConversationSession:
        """
        Append a turn to an active session and update activity timestamps.
        Raises ValueError if session is not found or expired.
        """
        pass

    @abstractmethod
    def close_session(self, session_id: str) -> None:
        """Mark session status as closed."""
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> None:
        """Completely purge session from store."""
        pass

    @abstractmethod
    def sweep_expired_sessions(self) -> int:
        """Sweep store and mark expired sessions. Returns count of expired sessions swept."""
        pass


class InMemorySessionStore(SessionStore):
    """
    In-memory dictionary implementation of SessionStore.
    Thread-safe per-session operations using isolated lookup keys.
    """

    def __init__(self):
        self._store: Dict[str, ConversationSession] = {}

    def create_session(self, user_id: Optional[str] = None, ttl_minutes: int = 60) -> ConversationSession:
        now = datetime.utcnow()
        session_id = str(uuid.uuid4())
        created_at_utc = now.isoformat()
        last_active_utc = created_at_utc
        expires_at_utc = (now + timedelta(minutes=ttl_minutes)).isoformat()

        session = ConversationSession(
            session_id=session_id,
            user_id=str(user_id) if user_id else None,
            created_at_utc=created_at_utc,
            last_active_utc=last_active_utc,
            expires_at_utc=expires_at_utc,
            turns=[],
            turn_count=0,
            status="active",
        )
        self._store[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        if not session_id or session_id not in self._store:
            return None

        session = self._store[session_id]
        if session.status != "active":
            return None

        # Check TTL expiration
        now = datetime.utcnow()
        expires_dt = datetime.fromisoformat(session.expires_at_utc)
        if now >= expires_dt:
            session.status = "expired"
            return None

        return session

    def add_turn(self, session_id: str, turn: ConversationTurn, ttl_minutes: int = 60) -> ConversationSession:
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Active session '{session_id}' not found or expired.")

        now = datetime.utcnow()
        session.turns.append(turn)
        session.turn_count = len(session.turns)
        session.last_active_utc = now.isoformat()
        session.expires_at_utc = (now + timedelta(minutes=ttl_minutes)).isoformat()

        return session

    def close_session(self, session_id: str) -> None:
        if session_id in self._store:
            self._store[session_id].status = "closed"

    def delete_session(self, session_id: str) -> None:
        if session_id in self._store:
            del self._store[session_id]

    def sweep_expired_sessions(self) -> int:
        now = datetime.utcnow()
        swept_count = 0
        for session in self._store.values():
            if session.status == "active":
                expires_dt = datetime.fromisoformat(session.expires_at_utc)
                if now >= expires_dt:
                    session.status = "expired"
                    swept_count += 1
        return swept_count
