from fastapi import APIRouter, Request, status
from typing import Dict, Any
import time

from app.core.config import settings
from app.api.schemas.responses import ApiResponse, MetaResponse

# Initialize router for health endpoints
router = APIRouter()

# Store startup time for uptime calculation
app_startup_time = time.time()

@router.get(
    "/health",
    summary="Detailed Health Check",
    response_model=ApiResponse[Dict[str, Any]], # Explicitly use our ApiResponse model
    status_code=status.HTTP_200_OK,
)
async def health_check_detailed(request: Request) -> ApiResponse[Dict[str, Any]]:
    """
    Returns a detailed health status of the application.
    Includes application status, version, environment, and uptime.
    """
    current_time = time.time()
    uptime_seconds = current_time - app_startup_time
    uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"

    health_info = {
        "status": "healthy",
        "version": settings.APP_NAME, # Using APP_NAME for version for now, can be replaced by actual versioning later
        "environment": settings.ENVIRONMENT,
        "uptime": uptime_str,
        "debug_mode": settings.DEBUG
    }
    
    return ApiResponse(
        message="Health check successful",
        data=health_info,
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp=request.headers.get("X-Response-Timestamp", "N/A") # Placeholder, will be set by middleware later
        )
    )

@router.get(
    "/",
    summary="API Version Root Endpoint",
    response_model=ApiResponse[Dict[str, str]],
    status_code=status.HTTP_200_OK,
)
async def api_root_endpoint(request: Request) -> ApiResponse[Dict[str, str]]:
    """
    Root endpoint for the API version, providing basic information.
    """
    return ApiResponse(
        message=f"Welcome to {settings.APP_NAME} API v1!",
        data={
            "version": settings.APP_NAME, # Using APP_NAME for version for now
            "environment": settings.ENVIRONMENT
        },
        meta=MetaResponse(
            request_id=getattr(request.state, "request_id", "N/A"),
            timestamp=request.headers.get("X-Response-Timestamp", "N/A") # Placeholder
        )
    )
