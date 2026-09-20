# src/api/errors.py
"""
Centralized Error Model and Exception Handlers for FastAPI (§11).
Translates internal domain exceptions into uniform, safe APIError responses.
"""

import logging
from uuid import uuid4
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


def get_request_id(request: Request) -> str:
    """Extracts request_id attached by middleware or generates a fallback UUID."""
    return getattr(request.state, "request_id", str(uuid4()))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Validation error: {exc.errors()}")
    error_body = APIError(
        error_code="validation_error",
        message="The request could not be validated.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_body.model_dump())


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Pydantic validation error: {exc.errors()}")
    error_body = APIError(
        error_code="validation_error",
        message="The request could not be validated.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error_body.model_dump())


async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.info(f"[{request_id}] Authentication failed")
    error_body = APIError(
        error_code="authentication_required",
        message="Authentication failed.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=error_body.model_dump())


async def account_creation_exception_handler(request: Request, exc: AccountCreationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.info(f"[{request_id}] Account creation conflict: {exc}")
    error_body = APIError(
        error_code="identifier_exists",
        message="An account with this identifier already exists.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error_body.model_dump())


async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.warning(f"[{request_id}] Authorization denied / Session access failure")
    error_body = APIError(
        error_code="session_not_accessible",
        message="Session not found or not accessible.",
        request_id=request_id,
    )
    # Uniform 403 Forbidden response for unauthorized/nonexistent sessions per §6, §11
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=error_body.model_dump())


async def processing_exception_handler(request: Request, exc: ValueError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Processing failure: {exc}")
    error_body = APIError(
        error_code="processing_failed",
        message="Unable to process this request right now.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_body.model_dump())


async def service_unavailable_exception_handler(request: Request, exc: ConnectionError) -> JSONResponse:
    request_id = get_request_id(request)
    logger.critical(f"[{request_id}] Service connection failure: {exc}")
    error_body = APIError(
        error_code="service_unavailable",
        message="Service temporarily unavailable.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=error_body.model_dump())


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = get_request_id(request)
    logger.error(f"[{request_id}] Unhandled exception: {exc}", exc_info=True)
    error_body = APIError(
        error_code="internal_error",
        message="An unexpected error occurred.",
        request_id=request_id,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_body.model_dump())
