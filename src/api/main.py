# src/api/main.py
"""
FastAPI Application Factory & Lifespan Assembly (§4, §10, §12).
Registers CORS, request ID tracing, payload size limiters, Content-Type enforcement,
redaction logging, and hardened exception handlers.
"""

import logging
import time
from uuid import uuid4
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.api.config import get_api_settings
from src.api.hardening.middleware import (
    ContentTypeFilterMiddleware,
    REQUEST_ID_REGEX,
)
from src.api.hardening.redaction import RedactionFilter, JsonAccessLogFormatter
from src.api.errors import (
    validation_exception_handler,
    pydantic_validation_exception_handler,
    authentication_exception_handler,
    account_creation_exception_handler,
    authorization_exception_handler,
    session_busy_exception_handler,
    rate_limited_exception_handler,
    server_busy_exception_handler,
    dependency_unavailable_exception_handler,
    upstream_timeout_exception_handler,
    upstream_failure_exception_handler,
    unhandled_exception_handler,
    SessionBusyError,
    RateLimitedError,
    ServerBusyError,
    DependencyUnavailableError,
    UpstreamTimeoutError,
    UpstreamFailureError,
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

logger = logging.getLogger("api.access")


def setup_access_logging(settings):
    """Configures structured JSON logging with sensitive data redaction filter (§10)."""
    if settings.log_redaction_enabled:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonAccessLogFormatter())
        handler.addFilter(RedactionFilter())
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager initializing database connections once at startup (§4)."""
    settings = get_api_settings()
    # Startup validation (§12)
    settings.validate()
    init_app_dependencies()
    yield


def create_app() -> FastAPI:
    """Factory creating and configuring the hardened FastAPI application instance."""
    settings = get_api_settings()
    setup_access_logging(settings)

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title="BetterCallSaul RAG API",
        description="Phase 3.1 Hardened Production API for Grounded Legal RAG",
        version="3.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    # 1. CORS Middleware (§10)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request Tracing, Size Cap & Timing Middleware (§6, §10)

    @app.middleware("http")
    async def tracing_size_and_timing_middleware(request: Request, call_next):
        start_time = time.time()

        # Validate inbound X-Request-ID or generate standard UUID (§6)
        inbound_req_id = request.headers.get("X-Request-ID", "").strip()
        if inbound_req_id and REQUEST_ID_REGEX.match(inbound_req_id):
            req_id = inbound_req_id
        else:
            req_id = str(uuid4())

        request.state.request_id = req_id

        # Enforce payload size limit on Content-Length (§6)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.request_size_limit_bytes:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error_code": "payload_too_large",
                            "message": f"Request payload exceeds max limit of {settings.request_size_limit_bytes} bytes.",
                            "request_id": req_id,
                        },
                    )
            except ValueError:
                pass

        response = await call_next(request)

        latency_ms = round((time.time() - start_time) * 1000.0, 3)

        # Echo Request ID and Security Headers
        response.headers["X-Request-ID"] = req_id
        if settings.response_timing_header:
            response.headers["X-Process-Time-Ms"] = str(latency_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"

        # Access Logging (§10)
        if request.url.path not in settings.access_log_exclude_paths:
            route_template = request.scope.get("path", request.url.path)
            logger.info(
                f"{request.method} {route_template} {response.status_code} ({latency_ms} ms)",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "route_template": route_template,
                    "status_code": response.status_code,
                    "latency_ms": latency_ms,
                },
            )

        return response

    # 4. Exception Handlers Registration (§4.2, §11)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(AccountCreationError, account_creation_exception_handler)
    app.add_exception_handler(AuthorizationError, authorization_exception_handler)
    app.add_exception_handler(SessionBusyError, session_busy_exception_handler)
    app.add_exception_handler(RateLimitedError, rate_limited_exception_handler)
    app.add_exception_handler(ServerBusyError, server_busy_exception_handler)
    app.add_exception_handler(DependencyUnavailableError, dependency_unavailable_exception_handler)
    app.add_exception_handler(UpstreamTimeoutError, upstream_timeout_exception_handler)
    app.add_exception_handler(UpstreamFailureError, upstream_failure_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 5. Mount Routers (§5)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(sessions_router)
    app.include_router(turns_router)

    return app


app = create_app()
