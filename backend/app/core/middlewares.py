import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import app_logger # Use our named application logger

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each incoming request.
    If 'X-Request-ID' header is present, it's used; otherwise, a new UUID is generated.
    The request ID is added to the request's state and can be included in logs.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class TimingAndLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log request details, measure execution time, and log response details.
    Includes request_id from request.state for contextual logging.
    """
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.perf_counter()

        # Prepare log extra for request logging
        request_log_extra = {
            "request_id": request.state.request_id if hasattr(request.state, 'request_id') else "N/A",
            "route": request.url.path,
            "method": request.method,
        }
        app_logger.info("Incoming request", extra=request_log_extra)

        response = await call_next(request)

        end_time = time.perf_counter()
        process_time = (end_time - start_time) * 1000 # in milliseconds

        # Prepare log extra for response logging
        response_log_extra = {
            "request_id": request.state.request_id if hasattr(request.state, 'request_id') else "N/A",
            "route": request.url.path,
            "method": request.method,
            "status_code": response.status_code,
            "duration": process_time,
        }
        app_logger.info("Outgoing response", extra=response_log_extra)

        return response

# Placeholder for future authentication middleware
class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # TODO: Implement actual authentication logic here in future phases
        # For now, it just passes through.
        app_logger.debug(f"Authentication placeholder middleware executed for RequestID: {getattr(request.state, 'request_id', 'N/A')}")
        response = await call_next(request)
        return response

def add_middlewares(app: ASGIApp) -> None:
    """
    Adds all custom and standard FastAPI middlewares to the application.
    Order matters: Request ID -> CORS -> Authentication (placeholder) -> Timing/Logging.
    """
    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"]
    )
    
    app.add_middleware(AuthenticationMiddleware) # Placeholder
    app.add_middleware(TimingAndLoggingMiddleware)

    # Note: FastAPI middlewares are processed in reverse order of addition on the response path.
    # So, TimingAndLoggingMiddleware will run first on response, then Auth, then CORS, then RequestID.
    # On request path, it's normal order.
