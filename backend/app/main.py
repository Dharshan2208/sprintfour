from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import app_logger, configure_logging
from app.core.middlewares import add_middlewares
from app.core.error_handlers import register_exception_handlers
from app.api.main import api_router # This router will aggregate v1 routes

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Context manager for managing the application's lifespan events.
    Executed on startup and shutdown of the FastAPI application.
    """
    configure_logging() # Configure logging as the very first step
    app_logger.info(f"Application startup: {settings.APP_NAME} (Environment: {settings.ENVIRONMENT})")

    # TODO: Initialize database, Redis, message queues, etc. here in future phases
    # Example: await database.connect()

    yield # Application starts serving requests

    app_logger.info(f"Application shutdown: {settings.APP_NAME} (Environment: {settings.ENVIRONMENT})")
    # TODO: Clean up resources here in future phases
    # Example: await database.disconnect()

def create_app() -> FastAPI:
    """
    Factory function to create and configure the FastAPI application instance.
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0", # Base API version for overall app
        openapi_url=f"/openapi.json" if settings.DEBUG else None, # Disable OpenAPI in prod
        docs_url=f"/docs" if settings.DEBUG else None, # Disable Swagger UI in prod
        redoc_url=f"/redoc" if settings.DEBUG else None, # Disable ReDoc in prod
        lifespan=lifespan,
        debug=settings.DEBUG
    )

    # Register global middleware
    add_middlewares(app)

    # Register global exception handlers
    register_exception_handlers(app)

    # Include API routers (e.g., /api/v1)
    app.include_router(api_router, prefix="/api")

    @app.get("/", tags=["Health"], summary="Root endpoint")
    async def root_endpoint() -> Dict[str, str]:
        """
        Root endpoint providing basic application information.
        """
        return {"message": "Welcome to the Anonymization Service API! Check /health for status."}

    return app
