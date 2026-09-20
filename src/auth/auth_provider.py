# src/auth/auth_provider.py
"""
Authentication Provider Abstraction and Password-based Implementation (§8).
Supports account creation, authentication, token issuance, token validation, and logout across PostgreSQL, SQLite, and In-Memory.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
import hashlib
import sqlite3
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from src.auth.schemas import (
    User,
    AuthenticatedUser,
    AuthenticationError,
    AuthorizationError,
    AccountCreationError,
)
from src.auth.password_hashing import hash_password, verify_password
from src.auth.rate_limiter import LoginRateLimiter


class AuthProvider(ABC):
    """Abstract protocol for authentication providers (§8)."""

    @abstractmethod
    def create_account(self, auth_identifier: str, raw_password: str) -> User:
        """Creates a new user account."""
        pass

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> tuple[AuthenticatedUser, str]:
        """
        Authenticates credentials and returns (AuthenticatedUser, raw_token_string).
        credentials dict: {"auth_identifier": "...", "password": "..."}
        """
        pass

    @abstractmethod
    def validate_token(self, token: str) -> AuthenticatedUser:
        """Validates a session token and returns AuthenticatedUser or raises AuthenticationError."""
        pass

    @abstractmethod
    def logout(self, token: str) -> None:
        """Revokes an active session token."""
        pass


class PasswordAuthProvider(AuthProvider):
    """
    Password-based AuthProvider implementation (§8, §12, §13).
    Supports SQLite, PostgreSQL, or In-Memory backends.
    """

    def __init__(
        self,
        backend: str = "in_memory",
        db_connection=None,
        sqlite_path: Optional[str] = None,
        db_config: Optional[Dict[str, Any]] = None,
        token_ttl_minutes: int = 60,
        min_password_length: int = 8,
        rate_limiter: Optional[LoginRateLimiter] = None,
    ):
        self.backend = backend.lower()
        self.db_connection = db_connection
        self.sqlite_path = sqlite_path
        self.db_config = db_config or {}
        self.token_ttl_minutes = token_ttl_minutes
        self.min_password_length = min_password_length
        self.rate_limiter = rate_limiter or LoginRateLimiter()

        # In-memory storage structures
        self._in_memory_users: Dict[UUID, User] = {}
        self._in_memory_identifier_index: Dict[str, UUID] = {}
        self._in_memory_tokens: Dict[str, Dict[str, Any]] = {}

    def _get_connection(self):
        if self.db_connection is not None:
            return self.db_connection
        if self.backend == "sqlite" and self.sqlite_path:
            conn = sqlite3.connect(self.sqlite_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            return conn
        elif self.backend == "postgres":
            import psycopg2
            import os
            host = self.db_config.get("host", "localhost")
            port = self.db_config.get("port", 5432)
            database = self.db_config.get("database", "postgres")
            user = self.db_config.get("user", "postgres")
            password = os.getenv(self.db_config.get("password_env_var", "POSTGRES_PASSWORD"), "postgres")
            return psycopg2.connect(host=host, port=port, dbname=database, user=user, password=password)
        return None

    def _normalize_identifier(self, identifier: str) -> str:
        if not identifier:
            return ""
        return identifier.strip().lower()

    def _hash_token(self, token_str: str) -> str:
        """Hashes bearer token for storage at rest (§12)."""
        return hashlib.sha256(token_str.encode("utf-8")).hexdigest()

    def create_account(self, auth_identifier: str, raw_password: str) -> User:
        """Creates a new account after validating credentials and uniqueness (§13)."""
        normalized_id = self._normalize_identifier(auth_identifier)
        if not normalized_id:
            raise AccountCreationError("Authentication identifier cannot be empty.")

        if not raw_password or len(raw_password) < self.min_password_length:
            raise AccountCreationError(
                f"Password must be at least {self.min_password_length} characters long."
            )

        pass_hash = hash_password(raw_password)
        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        user_id = uuid4()
        user = User(
            user_id=user_id,
            auth_identifier=normalized_id,
            status="active",
            password_hash=pass_hash,
            created_at_utc=now,
            last_login_at_utc=None,
        )

        conn = self._get_connection()
        if conn is not None:
            close_after = (self.db_connection is None)
            try:
                if self.backend == "sqlite" or isinstance(conn, sqlite3.Connection):
                    with conn:
                        conn.execute(
                            "INSERT INTO users (user_id, auth_identifier, password_hash, status, created_at_utc) VALUES (?, ?, ?, ?, ?)",
                            (str(user_id), normalized_id, pass_hash, "active", now_str),
                        )
                else:
                    schema = self.db_config.get("schema", "session_db")
                    with conn.cursor() as cursor:
                        cursor.execute(
                            f"INSERT INTO {schema}.users (user_id, auth_identifier, password_hash, status, created_at_utc) VALUES (%s, %s, %s, %s, %s)",
                            (str(user_id), normalized_id, pass_hash, "active", now),
                        )
                    conn.commit()
            except Exception as e:
                if self.db_connection and hasattr(self.db_connection, "rollback"):
                    self.db_connection.rollback()
                raise AccountCreationError(f"Account with identifier '{normalized_id}' already exists.") from e
            finally:
                if close_after:
                    conn.close()
        else:
            if normalized_id in self._in_memory_identifier_index:
                raise AccountCreationError(f"Account with identifier '{normalized_id}' already exists.")
            self._in_memory_users[user_id] = user
            self._in_memory_identifier_index[normalized_id] = user_id

        return user

    def authenticate(self, credentials: Dict[str, Any]) -> tuple[AuthenticatedUser, str]:
        """Authenticates a user and issues a token (§13)."""
        auth_identifier = credentials.get("auth_identifier", "")
        raw_password = credentials.get("password", "")

        normalized_id = self._normalize_identifier(auth_identifier)

        if self.rate_limiter.is_rate_limited(normalized_id):
            raise AuthenticationError("Too many failed login attempts. Please try again later.")

        generic_error = AuthenticationError("Invalid credentials or authentication failed.")
        user: Optional[User] = None

        conn = self._get_connection()
        if conn is not None:
            close_after = (self.db_connection is None)
            try:
                if self.backend == "sqlite" or isinstance(conn, sqlite3.Connection):
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT user_id, auth_identifier, password_hash, status, created_at_utc, last_login_at_utc FROM users WHERE auth_identifier = ?",
                        (normalized_id,),
                    )
                    row = cur.fetchone()
                    if row:
                        user = User(
                            user_id=UUID(str(row[0])),
                            auth_identifier=row[1],
                            password_hash=row[2],
                            status=row[3],
                            created_at_utc=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            last_login_at_utc=datetime.fromisoformat(row[5]) if row[5] else None,
                        )
                else:
                    schema = self.db_config.get("schema", "session_db")
                    with conn.cursor() as cur:
                        cur.execute(
                            f"SELECT user_id, auth_identifier, password_hash, status, created_at_utc, last_login_at_utc FROM {schema}.users WHERE auth_identifier = %s",
                            (normalized_id,),
                        )
                        row = cur.fetchone()
                        if row:
                            user = User(
                                user_id=UUID(str(row[0])),
                                auth_identifier=row[1],
                                password_hash=row[2],
                                status=row[3],
                                created_at_utc=row[4],
                                last_login_at_utc=row[5],
                            )
            except Exception:
                pass
            finally:
                if close_after:
                    conn.close()
        else:
            uid = self._in_memory_identifier_index.get(normalized_id)
            if uid:
                user = self._in_memory_users.get(uid)

        if not user or user.status != "active" or not user.password_hash:
            self.rate_limiter.record_failure(normalized_id)
            raise generic_error

        if not verify_password(raw_password, user.password_hash):
            self.rate_limiter.record_failure(normalized_id)
            raise generic_error

        # Success - reset rate limiter
        self.rate_limiter.reset(normalized_id)

        now = datetime.now(timezone.utc)
        now_str = now.isoformat()
        expires_at = now + timedelta(minutes=self.token_ttl_minutes)
        expires_at_str = expires_at.isoformat()
        raw_token = f"token_{uuid4().hex}"
        hashed_token = self._hash_token(raw_token)

        user.last_login_at_utc = now

        conn = self._get_connection()
        if conn is not None:
            close_after = (self.db_connection is None)
            try:
                if self.backend == "sqlite" or isinstance(conn, sqlite3.Connection):
                    with conn:
                        conn.execute("UPDATE users SET last_login_at_utc = ? WHERE user_id = ?", (now_str, str(user.user_id)))
                        conn.execute(
                            "INSERT INTO auth_sessions (token_id, user_id, issued_at_utc, expires_at_utc, revoked) VALUES (?, ?, ?, ?, ?)",
                            (hashed_token, str(user.user_id), now_str, expires_at_str, 0),
                        )
                else:
                    schema = self.db_config.get("schema", "session_db")
                    with conn.cursor() as cur:
                        cur.execute(f"UPDATE {schema}.users SET last_login_at_utc = %s WHERE user_id = %s", (now, str(user.user_id)))
                        cur.execute(
                            f"INSERT INTO {schema}.auth_sessions (token_id, user_id, issued_at_utc, expires_at_utc, revoked) VALUES (%s, %s, %s, %s, %s)",
                            (hashed_token, str(user.user_id), now, expires_at, False),
                        )
                    conn.commit()
            except Exception as e:
                if self.db_connection and hasattr(self.db_connection, "rollback"):
                    self.db_connection.rollback()
                raise AuthenticationError("Failed to store authentication session.") from e
            finally:
                if close_after:
                    conn.close()
        else:
            self._in_memory_users[user.user_id] = user
            self._in_memory_tokens[raw_token] = {
                "token_id": hashed_token,
                "user_id": user.user_id,
                "issued_at_utc": now,
                "expires_at_utc": expires_at,
                "revoked": False,
            }

        auth_user = AuthenticatedUser(
            user_id=user.user_id,
            auth_identifier=user.auth_identifier,
            issued_at_utc=now,
            expires_at_utc=expires_at,
        )

        return auth_user, raw_token

    def validate_token(self, token: str) -> AuthenticatedUser:
        """Validates bearer token (§13)."""
        if not token:
            raise AuthenticationError("Authentication required.")

        hashed_token = self._hash_token(token)
        now = datetime.now(timezone.utc)
        generic_error = AuthenticationError("Invalid, expired, or revoked authentication token.")

        conn = self._get_connection()
        if conn is not None:
            close_after = (self.db_connection is None)
            try:
                if self.backend == "sqlite" or isinstance(conn, sqlite3.Connection):
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT a.user_id, a.issued_at_utc, a.expires_at_utc, a.revoked, u.auth_identifier, u.status FROM auth_sessions a JOIN users u ON a.user_id = u.user_id WHERE a.token_id = ?",
                        (hashed_token,),
                    )
                    row = cur.fetchone()
                    if not row:
                        raise generic_error

                    user_id, issued_at_val, expires_at_val, revoked_val, auth_identifier, user_status = row
                    expires_at = datetime.fromisoformat(expires_at_val) if isinstance(expires_at_val, str) else expires_at_val
                    issued_at = datetime.fromisoformat(issued_at_val) if isinstance(issued_at_val, str) else issued_at_val
                    revoked = bool(revoked_val)
                else:
                    schema = self.db_config.get("schema", "session_db")
                    with conn.cursor() as cur:
                        cur.execute(
                            f"SELECT a.user_id, a.issued_at_utc, a.expires_at_utc, a.revoked, u.auth_identifier, u.status FROM {schema}.auth_sessions a JOIN {schema}.users u ON a.user_id = u.user_id WHERE a.token_id = %s",
                            (hashed_token,),
                        )
                        row = cur.fetchone()
                        if not row:
                            raise generic_error

                        user_id, issued_at, expires_at, revoked, auth_identifier, user_status = row

                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if issued_at.tzinfo is None:
                    issued_at = issued_at.replace(tzinfo=timezone.utc)

                if revoked or expires_at <= now or user_status != "active":
                    raise generic_error

                return AuthenticatedUser(
                    user_id=UUID(str(user_id)),
                    auth_identifier=auth_identifier,
                    issued_at_utc=issued_at,
                    expires_at_utc=expires_at,
                )
            except AuthenticationError:
                raise
            except Exception as e:
                raise generic_error from e
            finally:
                if close_after:
                    conn.close()
        else:
            token_data = self._in_memory_tokens.get(token)
            if not token_data:
                raise generic_error

            if token_data["revoked"] or token_data["expires_at_utc"] <= now:
                raise generic_error

            user = self._in_memory_users.get(token_data["user_id"])
            if not user or user.status != "active":
                raise generic_error

            return AuthenticatedUser(
                user_id=user.user_id,
                auth_identifier=user.auth_identifier,
                issued_at_utc=token_data["issued_at_utc"],
                expires_at_utc=token_data["expires_at_utc"],
            )

    def logout(self, token: str) -> None:
        """Revokes an active authentication token (§13)."""
        if not token:
            return

        hashed_token = self._hash_token(token)
        conn = self._get_connection()
        if conn is not None:
            close_after = (self.db_connection is None)
            try:
                if self.backend == "sqlite" or isinstance(conn, sqlite3.Connection):
                    with conn:
                        conn.execute("UPDATE auth_sessions SET revoked = 1 WHERE token_id = ?", (hashed_token,))
                else:
                    schema = self.db_config.get("schema", "session_db")
                    with conn.cursor() as cur:
                        cur.execute(f"UPDATE {schema}.auth_sessions SET revoked = TRUE WHERE token_id = %s", (hashed_token,))
                    conn.commit()
            except Exception:
                if self.db_connection and hasattr(self.db_connection, "rollback"):
                    self.db_connection.rollback()
            finally:
                if close_after:
                    conn.close()
        else:
            if token in self._in_memory_tokens:
                self._in_memory_tokens[token]["revoked"] = True
