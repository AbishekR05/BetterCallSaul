# src/auth/authorization_service.py
"""
Authorization Service for Session Ownership Verification (§9).
Enforces that authenticated users can only access sessions they own.
"""

from typing import Union
from uuid import UUID

from src.auth.schemas import (
    AuthenticatedUser,
    AuthenticationError,
    AuthorizationError,
)
from src.conversation.session_store import SessionStore


class AuthorizationService:
    """
    Authorization Service enforcing explicit session ownership (§9).
    """

    def __init__(self, session_store: SessionStore):
        self.session_store = session_store

    def authorize_session_access(
        self,
        authenticated_user: AuthenticatedUser,
        session_id: Union[UUID, str],
        action: str = "read",
    ) -> bool:
        """
        Verifies if an authenticated user is authorized to read/write/delete a specific session (§9, §14).
        Raises AuthorizationError if the session does not exist or belongs to another user.
        Raises AuthenticationError if user context is missing.
        """
        if not authenticated_user or not getattr(authenticated_user, "user_id", None):
            raise AuthenticationError("Authentication required.")

        s_id = str(session_id)
        session = self.session_store.get_session(s_id)

        # Non-existent session or cross-user access returns the SAME generic error (§9, §14)
        generic_error = AuthorizationError("Session not found or not accessible.")

        if session is None:
            raise generic_error

        # Session model stores user_id
        session_owner_id = str(getattr(session, "user_id", ""))
        user_id = str(authenticated_user.user_id)

        if not session_owner_id or session_owner_id != user_id:
            raise generic_error

        return True
