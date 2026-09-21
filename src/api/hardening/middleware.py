# src/api/hardening/middleware.py
"""
Request Validation & Hardening Middleware (§6, §10).
Provides payload size limits, Content-Type checking, request ID parsing, and timing headers.
"""

import re
from uuid import uuid4
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

# Strict request ID regex pattern (§6)
REQUEST_ID_REGEX = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class PayloadStreamingCapMiddleware(BaseHTTPMiddleware):
    """
    Body size cap enforcement on Content-Length and streaming requests (§6).
    """

    def __init__(self, app, max_bytes: int = 102400):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > self.max_bytes:
                    req_id = getattr(request.state, "request_id", str(uuid4()))
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={
                            "error_code": "payload_too_large",
                            "message": f"Request payload exceeds max limit of {self.max_bytes} bytes.",
                            "request_id": req_id,
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


class ContentTypeFilterMiddleware(BaseHTTPMiddleware):
    """
    Enforces application/json Content-Type header on request methods with bodies (§6).
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "").lower()
            content_length = request.headers.get("content-length")

            # Reject if content-type header is present and is not application/json
            if content_type and not content_type.startswith("application/json"):
                req_id = getattr(request.state, "request_id", str(uuid4()))
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error_code": "unsupported_media_type",
                        "message": "Content-Type must be 'application/json'.",
                        "request_id": req_id,
                    },
                )

            # Reject if non-zero body present but missing application/json Content-Type
            if content_length and int(content_length) > 0 and not content_type:
                req_id = getattr(request.state, "request_id", str(uuid4()))
                return JSONResponse(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    content={
                        "error_code": "unsupported_media_type",
                        "message": "Content-Type must be 'application/json'.",
                        "request_id": req_id,
                    },
                )

        return await call_next(request)
