from typing import Generic, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, Field

T = TypeVar('T') # Generic type for data field

class MetaResponse(BaseModel):
    """
    Standard metadata for successful API responses.
    """
    request_id: str = Field(..., description="Unique ID for the request")
    timestamp: str = Field(..., description="UTC timestamp of the response in ISO 8601 format")
    # Add other common metadata fields here, e.g., pagination info

class ApiResponse(BaseModel, Generic[T]):
    """
    Standard structure for all successful API responses.
    """
    success: bool = Field(True, description="Indicates if the request was successful")
    message: str = Field("Operation successful", description="A human-readable message about the operation")
    data: Optional[T] = Field(None, description="The primary data returned by the API")
    meta: MetaResponse = Field(..., description="Metadata about the response")


class ErrorMetaResponse(BaseModel):
    """
    Metadata for error API responses.
    """
    status_code: int = Field(..., description="HTTP status code")
    error_code: str = Field(..., description="Application-specific error code (e.g., VALIDATION_ERROR)")
    timestamp: str = Field(..., description="UTC timestamp of the error in ISO 8601 format")
    request_id: str = Field(..., description="Unique ID for the request")

class ErrorResponse(BaseModel):
    """
    Standard structure for all API error responses.
    """
    success: bool = Field(False, description="Indicates if the request failed")
    message: str = Field(..., description="A human-readable message about the error")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional extra data related to the error, e.g., validation details")
    meta: ErrorMetaResponse = Field(..., description="Metadata about the error response")
