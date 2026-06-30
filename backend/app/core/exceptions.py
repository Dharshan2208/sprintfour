from typing import Dict, Any, Optional
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

class AppException(Exception):
    """
    Base exception for application-specific errors.
    All custom application exceptions should inherit from this class.
    """
    status_code: int = HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    message: str = "An unexpected error occurred."
    data: Optional[Dict[str, Any]] = None # Optional extra data to include in error response

    def __init__(
        self,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        if message: self.message = message
        if status_code: self.status_code = status_code
        if error_code: self.error_code = error_code
        if data: self.data = data
        super().__init__(self.message)


class BadRequestException(AppException):
    """
    Exception for bad client requests (e.g., malformed syntax, invalid arguments).
    Corresponds to HTTP 400 Bad Request.
    """
    status_code = HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    message = "The request was invalid or malformed."


class ValidationException(BadRequestException):
    """
    Exception for input validation failures.
    Inherits from BadRequestException, corresponds to HTTP 400 Bad Request.
    """
    error_code = "VALIDATION_ERROR"
    message = "Validation failed for one or more input parameters."


class ResourceNotFoundException(AppException):
    """
    Exception for when a requested resource is not found.
    Corresponds to HTTP 404 Not Found.
    """
    status_code = HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    message = "The requested resource could not be found."


class InternalServerException(AppException):
    """
    Generic exception for unexpected server-side errors.
    Corresponds to HTTP 500 Internal Server Error.
    """
    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "INTERNAL_SERVER_ERROR"
    message = "An internal server error occurred."
