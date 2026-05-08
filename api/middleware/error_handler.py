"""
Centralized error handling middleware for the FastAPI application.

Catches unhandled exceptions, validation errors, and known application
errors, returning consistent JSON via the ErrorResponse schema.
"""

import logging
import time
import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("dsa_bot.api.middleware")


class APIError(Exception):
    """Application-level error with HTTP status code."""

    def __init__(self, status_code: int, error: str, detail: str | None = None):
        self.status_code = status_code
        self.error = error
        self.detail = detail
        super().__init__(error)


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, resource: str, identifier: object = None):
        detail = f"{resource} not found"
        if identifier is not None:
            detail = f"{resource} with id '{identifier}' not found"
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class BadRequestError(APIError):
    """Client sent invalid data."""

    def __init__(self, detail: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


def _error_body(error: str, detail: str | None = None) -> dict:
    """Build a uniform error JSON body."""
    from datetime import datetime, timezone

    return {
        "success": False,
        "error": error,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI app."""

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        logger.warning("APIError %s %s → %d: %s", request.method, request.url.path,
                        exc.status_code, exc.error)
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.error, exc.detail),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(str(exc.detail)),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        first = errors[0] if errors else {}
        field = " → ".join(str(l) for l in first.get("loc", []))
        msg = first.get("msg", "Validation error")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(f"Validation error on '{field}': {msg}",
                                detail=str(errors)),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on %s %s:\n%s",
                      request.method, request.url.path,
                      traceback.format_exc())
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body("Internal server error",
                                detail="An unexpected error occurred."),
        )
