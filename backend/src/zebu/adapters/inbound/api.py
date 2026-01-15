"""API router configuration."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/")
async def root() -> dict[str, str]:
    """API root endpoint."""
    return {"message": "Welcome to PaperTrade API v1"}
