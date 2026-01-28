"""Lightweight health-check endpoint (no auth required)."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Return a simple JSON payload confirming the service is alive."""
    return {
        "status": "healthy",
        "service": "geolyze-api",
        "version": "1.0.0",
    }
