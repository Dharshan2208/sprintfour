from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router_v1

api_router = APIRouter()

# Include API version 1 routes
api_router.include_router(health_router_v1, prefix="/v1", tags=["Health"]) # Prefix /v1 for versioning

# Future API versions would be included here, e.g.:
# from app.api.v2.routes.some_resource import router as some_resource_router_v2
# api_router.include_router(some_resource_router_v2, prefix="/v2", tags=["Some Resource V2"])
