# src/api/errors.py
"""
Centralized Domain Exception Taxonomy and FastAPI Exception Handlers (§4.2, §11).
Translates all internal domain, database, timeout, and validation errors into
deterministic, safe APIError responses ({ error_code, message, request_id }).
"""

import logging
from uuid import uuid4
from typing import Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.api.schemas.error import APIError
from src.auth.schemas import (
    AuthenticationError,
    AuthorizationError,
    AccountCreationError,
)

logger = logging.getLogger("api.errors")


# Domain Hardening Exceptions
class SessionBusyError(Exception):
    """Raised when a concurrent turn is attempted on an active session (§4.2)."""
    pass


class RateLimitedError(Exception):
    """Raised when request rate limit is exceeded (§4.2, §5)."""
    def __init__(self, message: str = "Rate limit exceeded.", retry_after_s: int = 60):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class ServerBusyError(Exception):
    """Raised when global turn concurrency capacity is exceeded (§4.2, §5.7)."""
    def __init__(self, message: str = "Server busy.", retry_after_s: int = 5):
        super().__init__(message)
        self.retry_after_s = retry_after_s


class DependencyUnavailableError(Exception):
    """Raised when database or auth store is unreachable or fails (§4.2, §8)."""
    pass


class UpstreamTimeoutError(Exception):
    """Raised when RAG retrieval or LLM execution times out (§4.2, §9)."""
    pass


class UpstreamFailureError(Exception):
    """Raised when RAG retrieval or embedding/reranker execution fails (§4.2, §9)."""
    pass


class InvalidIdentifierError(Exception):
    """Raised when a path or parameter UUID is malformed (§4.2)."""
    pass


def get_request_id(request: Request) -> str:
    """Extracts request_id attached by middleware or generates a fallback UUID."""
    return getattr(request.state, "request_id", str(uuid4()))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Validation error: {exc.errors()}")

    # Distinguish path UUID validation failure from body validation
    is_path_id_error = any("session_id" in str(err.get("loc", [])) for err in exc.errors())
    error_code = "invalid_identifier" if is_path_id_error else "validation_error"
    msg = "Invalid session identifier format." if is_path_id_error else "The request body or parameters failed validation."

    error_body = APIError(
        error_code=error_code,
        message=msg,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_body.model_dump(),
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Pydantic validation error: {exc.errors()}")
    error_body = APIError(
        error_code="validation_error",
        message="The request payload failed validation.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_body.model_dump(),
    )


async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.info(f"[{request_id}] Authentication failed")
    error_body = APIError(
        error_code="unauthenticated",
        message="Authentication failed or token invalid.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_body.model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


async def account_creation_exception_handler(request: Request, exc: AccountCreationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.info(f"[{request_id}] Account creation conflict")
    error_body = APIError(
        error_code="conflict",
        message="An account with this identifier already exists.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_body.model_dump(),
    )


async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Authorization denied or session not found")
    error_body = APIError(
        error_code="session_not_found",
        message="Session not found.",
        request_id=request_id,
    )
    # Uniform 404 response for unauthorized/nonexistent sessions per §4.2, §4.8
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=error_body.model_dump(),
    )


async def session_busy_exception_handler(request: Request, exc: SessionBusyError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Session turn concurrency collision: {exc}")
    error_body = APIError(
        error_code="session_busy",
        message="Session has an active turn in progress.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=error_body.model_dump(),
    )


async def rate_limited_exception_handler(request: Request, exc: RateLimitedError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Rate limit exceeded")
    error_body = APIError(
        error_code="rate_limited",
        message="Too many requests. Please try again later.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=error_body.model_dump(),
        headers={"Retry-After": str(exc.retry_after_s)},
    )


async def server_busy_exception_handler(request: Request, exc: ServerBusyError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Turn capacity exceeded: {exc}")
    error_body = APIError(
        error_code="server_busy",
        message="Server is busy processing high turn capacity.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_body.model_dump(),
        headers={"Retry-After": str(exc.retry_after_s)},
    )


async def dependency_unavailable_exception_handler(request: Request, exc: DependencyUnavailableError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Dependency unavailable: {exc}")
    error_body = APIError(
        error_code="dependency_unavailable",
        message="Database or authentication service is temporarily unavailable.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=error_body.model_dump(),
    )


async def upstream_timeout_exception_handler(request: Request, exc: UpstreamTimeoutError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Upstream timeout: {exc}")
    error_body = APIError(
        error_code="upstream_timeout",
        message="Upstream generation or retrieval service timed out.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content=error_body.model_dump(),
    )


async def upstream_failure_exception_handler(request: Request, exc: UpstreamFailureError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Upstream failure: {exc}")
    error_body = APIError(
        error_code="upstream_failure",
        message="Upstream retrieval or generation service failed.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content=error_body.model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    error_body = APIError(
        error_code="internal_error",
        message="An unexpected server error occurred.",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_body.model_dump(),
    )
