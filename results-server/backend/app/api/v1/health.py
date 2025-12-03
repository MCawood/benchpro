"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check() -> dict:
    """Return server health status and version.

    This endpoint is unauthenticated for load balancer health checks.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "app_name": settings.app_name,
    }

