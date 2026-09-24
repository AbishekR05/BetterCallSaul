# src/api/services/session_service.py
"""
Thin Application Adapter for Session Operations (§4, §5, §8).
Translates HTTP DTO requests to/from Phase 2.8 SessionStore with database exception wrapping.
"""

import sqlite3
from datetime import datetime
from uuid import UUID
from typing import List

from src.api.schemas.session import (
    SessionResponse,
    SessionListResponse,
)
from src.conversation.session_store import SessionStore
from src.conversation.schemas import ConversationSession
from src.auth.schemas import AuthorizationError
from src.api.errors import DependencyUnavailableError


class SessionService:
    """Thin wrapper around SessionStore for HTTP routes with DB fault protection (§8)."""

    def __init__(self, session_store: SessionStore):
        self.session_store = session_store

    def _map_to_response(self, session: ConversationSession) -> SessionResponse:
        turn_list = []
        for t in getattr(session, "turns", []):
            answer_detail = ""
            citations = []
            if hasattr(t, "grounded_answer") and t.grounded_answer:
                answer_detail = getattr(t.grounded_answer, "answer_detail", "") or getattr(t.grounded_answer, "answer_summary", "")
                raw_cites = getattr(t.grounded_answer, "citations", [])
                citations = [c.model_dump() if hasattr(c, "model_dump") else dict(c) for c in raw_cites]
            turn_list.append({
                "turn_id": t.turn_id,
                "turn_index": t.turn_index,
                "user_query": t.user_query,
                "answer_detail": answer_detail,
                "citations": citations,
                "timestamp_utc": getattr(t, "timestamp_utc", ""),
            })

        return SessionResponse(
            session_id=UUID(session.session_id),
            created_at_utc=datetime.fromisoformat(session.created_at_utc),
            last_active_utc=datetime.fromisoformat(session.last_active_utc),
            expires_at_utc=datetime.fromisoformat(session.expires_at_utc),
            status=session.status,
            turn_count=session.turn_count,
            turns=turn_list,
        )

    def create_session(self, user_id: UUID) -> SessionResponse:
        try:
            session = self.session_store.create_session(user_id=str(user_id))
            return self._map_to_response(session)
        except (sqlite3.Error, ConnectionError, OSError) as e:
            raise DependencyUnavailableError(f"Session database failure during session creation: {e}") from e

    def get_session(self, session_id: str) -> SessionResponse:
        try:
            session = self.session_store.get_session(session_id)
        except (sqlite3.Error, ConnectionError, OSError) as e:
            raise DependencyUnavailableError(f"Session database failure during lookup: {e}") from e

        if not session:
            raise AuthorizationError("Session not found or not accessible.")
        return self._map_to_response(session)

    def list_sessions(self, user_id: UUID) -> SessionListResponse:
        """Returns sessions belonging exclusively to caller (§5, §8)."""
        uid_str = str(user_id)
        matched_sessions: List[SessionResponse] = []

        try:
            if hasattr(self.session_store, "_store"):
                # InMemorySessionStore
                for s in self.session_store._store.values():
                    if str(getattr(s, "user_id", "")) == uid_str and s.status == "active":
                        matched_sessions.append(self._map_to_response(s))
            elif hasattr(self.session_store, "_get_connection"):
                # PersistentSessionStore (SQLite / Postgres)
                conn = self.session_store._get_connection()
                try:
                    schema_prefix = f"{self.session_store.db_config.get('schema', 'session_db')}." if getattr(self.session_store, 'backend', '') == 'postgres' else ""
                    cur = conn.cursor()
                    if getattr(self.session_store, 'backend', '') == 'sqlite':
                        cur.execute("SELECT session_id, user_id, created_at_utc, last_active_utc, expires_at_utc, status, turn_count FROM sessions WHERE user_id = ? AND status = 'active' ORDER BY last_active_utc DESC", (uid_str,))
                    else:
                        cur.execute(f"SELECT session_id, user_id, created_at_utc, last_active_utc, expires_at_utc, status, turn_count FROM {schema_prefix}sessions WHERE user_id = %s AND status = 'active' ORDER BY last_active_utc DESC", (uid_str,))
                    
                    rows = cur.fetchall()
                    for row in rows:
                        sess = ConversationSession(
                            session_id=str(row[0]),
                            user_id=str(row[1]) if row[1] else None,
                            created_at_utc=str(row[2]),
                            last_active_utc=str(row[3]),
                            expires_at_utc=str(row[4]),
                            turns=[],
                            turn_count=row[6],
                            status=row[5]
                        )
                        matched_sessions.append(self._map_to_response(sess))
                finally:
                    conn.close()
        except (sqlite3.Error, ConnectionError, OSError) as e:
            raise DependencyUnavailableError(f"Session database failure during list operation: {e}") from e

        return SessionListResponse(sessions=matched_sessions)

    def delete_session(self, session_id: str) -> None:
        try:
            self.session_store.delete_session(session_id)
        except (sqlite3.Error, ConnectionError, OSError) as e:
            raise DependencyUnavailableError(f"Session database failure during deletion: {e}") from e
