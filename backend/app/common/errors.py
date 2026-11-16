"""
Standard Error Responses and Exception Handlers
Follows the UniNova API contract specification (docs/backend/04-api-contract.md).
"""

import logging
from typing import Any, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import get_settings

logger = logging.getLogger("uninova.errors")
settings = get_settings()


def _add_cors_headers(request: Request, response: JSONResponse) -> JSONResponse:
    """Ensure CORS headers are present on all error responses so browsers don't mask error payloads."""
    origin = request.headers.get("origin")
    if origin:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[List[Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class AppException(Exception):
    """Base application exception with status code and error code."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[Any]] = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return _add_cors_headers(
            request,
            JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": exc.details or [],
                    }
                },
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            429: "TOO_MANY_REQUESTS",
            500: "INTERNAL_SERVER_ERROR",
        }
        return _add_cors_headers(
            request,
            JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": code_map.get(exc.status_code, "HTTP_ERROR"),
                        "message": exc.detail or "An HTTP error occurred.",
                        "details": [],
                    }
                },
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        formatted_errors = []
        for err in exc.errors():
            formatted_errors.append({
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            })

        return _add_cors_headers(
            request,
            JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Input validation failed. Please check the request fields.",
                        "details": formatted_errors,
                    }
                },
            ),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "Unhandled server exception on %s %s: %s",
            request.method,
            request.url.path,
            exc,
            exc_info=True,
        )
        error_details = [str(exc)] if settings.DEBUG else []
        return _add_cors_headers(
            request,
            JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": str(exc) if settings.DEBUG else "An unexpected internal server error occurred.",
                        "details": error_details,
                    }
                },
            ),
        )
