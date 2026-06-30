from typing import Dict, Any, Optional
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
)

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


# ──────────────────────────────────────────────────────────────────────
# Phase 2 — Document Processing Exceptions
# ──────────────────────────────────────────────────────────────────────

class DocumentExtractionException(BadRequestException):
    """
    Raised when text extraction from a document file fails.
    The file may be corrupt, encrypted, or in an unsupported sub-format.

    HTTP 400 — the user's file is the problem; they need to provide a
    valid document.
    """
    error_code = "DOCUMENT_EXTRACTION_FAILED"
    message = "Failed to extract text from the document. The file may be corrupted or encrypted."


class UnsupportedFileException(BadRequestException):
    """
    Raised when the uploaded file type is not supported by the system.

    HTTP 400 — the user provided a file format we don't handle (e.g.,
    .xlsx, .odt, image-only PDF).
    """
    error_code = "UNSUPPORTED_FILE_TYPE"
    message = "The uploaded file type is not supported. Supported types: TXT, PDF, DOCX."


class NormalizationException(InternalServerException):
    """
    Raised when text normalization fails unexpectedly.

    HTTP 500 — if valid extracted text cannot be normalized, something
    is wrong internally. The user cannot fix this.
    """
    error_code = "NORMALIZATION_FAILED"
    message = "Failed to normalize extracted document text."


# ──────────────────────────────────────────────────────────────────────
# Phase 3 — Detection Exceptions
# ──────────────────────────────────────────────────────────────────────

class DetectionException(InternalServerException):
    """
    Raised when the detection pipeline encounters an unexpected error.

    HTTP 500 — internal logic error in one of the detectors, merger,
    or confidence engine.
    """
    error_code = "DETECTION_FAILED"
    message = "An error occurred during PII detection."


class GeminiException(AppException):
    """
    Raised when the upstream Gemini API fails.

    HTTP 502 (Bad Gateway) — the upstream service is unavailable,
    returned an error, or gave unparseable output. This is distinct
    from a generic 500 so monitoring can alert on upstream health.
    """
    status_code = HTTP_502_BAD_GATEWAY
    error_code = "GEMINI_API_ERROR"
    message = "The AI detection service (Gemini) returned an error or is unavailable."
