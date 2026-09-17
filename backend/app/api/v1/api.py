from fastapi import APIRouter
from app.api.v1.endpoints import health, channels, videos, analytics

api_router = APIRouter()

# Register endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(channels.router, prefix="/channels", tags=["Channels"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
