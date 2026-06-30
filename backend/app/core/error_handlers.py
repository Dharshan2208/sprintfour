import traceback
from typing import Union, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError

from app.core.config import settings
from app.core.exceptions import AppException, InternalServerException
from app.core.logging import app_logger # Use our named application logger
from app.api.schemas.responses import ErrorResponse # We'll define this schema next

def build_error_response(
    request: Request,
    exc: Union[AppException, HTTPException, RequestValidationError, Exception],
    status_code: int,
    error_code: str,
    message: str,
    data: Dict[str, Any] = None
) -> JSONResponse:
    """
    Helper function to build a consistent JSON error response.
    """
    error_response = ErrorResponse(
        success=False,
        message=message,
        data=data,
        meta={
            "status_code": status_code,
            "error_code": error_code,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request_id": getattr(request.state, "request_id", "N/A")
        }
    )

    # Log the error with relevant context
    log_extra = {
        "request_id": getattr(request.state, "request_id", "N/A"),
        "route": request.url.path,
        "method": request.method,
        "status_code": status_code,
        "error_code": error_code,
        "message": message,
    }
    if status_code >= 500: # Log 5xx errors as ERROR level, include stack trace
        app_logger.error("Server Error: %s", message, exc_info=exc, extra=log_extra)
    elif status_code >= 400: # Log 4xx errors as WARNING level
        app_logger.warning("Client Error: %s", message, extra=log_extra)
    else: # Should not happen for errors, but as a fallback
        app_logger.error("Unhandled Error: %s", message, exc_info=exc, extra=log_extra)

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True)
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handles custom AppException instances.
    """
    return build_error_response(
        request,
        exc,
        exc.status_code,
        exc.error_code,
        exc.message,
        exc.data
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles FastAPI's HTTPException.
    """
    return build_error_response(
        request,
        exc,
        exc.status_code,
        exc.detail, # detail from HTTPException is the message
        str(exc.status_code) # Use status code as error_code string for generic HTTPException
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles FastAPI's RequestValidationError (Pydantic validation errors).
    """
    # FastAPI's default for RequestValidationError includes `body` details.
    # We extract relevant parts to fit our `data` structure for validation errors.
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"]
        })
    
    return build_error_response(
        request,
        exc,
        status.HTTP_422_UNPROCESSABLE_ENTITY, # Standard for validation errors
        "VALIDATION_ERROR",
        "One or more validation errors occurred.",
        data={"errors": errors}
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exceptions.
    Treats them as Internal Server Errors.
    """
    internal_exc = InternalServerException() # Use our InternalServerException for consistency
    return build_error_response(
        request,
        exc,
        internal_exc.status_code,
        internal_exc.error_code,
        internal_exc.message # Use the generic message for unhandled errors
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers all custom exception handlers with the FastAPI application.
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler) # Catch-all, should be last
