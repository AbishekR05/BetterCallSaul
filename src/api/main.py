# src/api/main.py
"""
FastAPI Application Factory & Lifespan Assembly (§4, §10).
Registers CORS, request tracing, payload size limiters, security headers, and exception handlers.
"""

from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.api.config import get_api_settings
from src.api.errors import (
    validation_exception_handler,
    pydantic_validation_exception_handler,
    authentication_exception_handler,
    account_creation_exception_handler,
    authorization_exception_handler,
    processing_exception_handler,
    service_unavailable_exception_handler,
    unhandled_exception_handler,
)
from src.api.routers import (
    health_router,
    auth_router,
    sessions_router,
    turns_router,
)
from src.api.dependencies import init_app_dependencies
from src.auth.schemas import (
    AuthenticationError,
    AuthorizationError,
    AccountCreationError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager initializing database connections once at startup (§4)."""
    init_app_dependencies()
    yield


def create_app() -> FastAPI:
    """Factory creating and configuring the FastAPI application instance."""
    settings = get_api_settings()

    app = FastAPI(
        title="BetterCallSaul RAG API",
        description="Phase 3.0 Production API & Backend Architecture for Grounded Legal RAG",
        version="3.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # 1. CORS Middleware (§10)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request ID & Security Headers Middleware (§10)
    @app.middleware("http")
    async def security_and_tracing_middleware(request: Request, call_next):
        # Extract or generate request ID
        req_id = request.headers.get("X-Request-ID", str(uuid4()))
        request.state.request_id = req_id

        # Body size cap enforcement (§10)
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.request_size_limit_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error_code": "payload_too_large",
                    "message": "Request payload exceeds size limit.",
                    "request_id": req_id,
                },
            )

        response = await call_next(request)

        # Security Headers (§10)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        return response

    # 3. Exception Handlers Registration (§11)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AccountCreationError, account_creation_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(ValueError, processing_exception_handler)
    app.add_exception_handler(ConnectionError, service_unavailable_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 4. Mount Routers (§5)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(turns_router)

    return app


app = create_app()
