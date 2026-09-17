from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db
from app.services.scheduler import scheduler

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any], status_code=status.HTTP_200_OK)
def check_health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint returning system status, database health, YouTube API status, and scheduler state.
    """
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "youtube_api_configured": bool(settings.YOUTUBE_API_KEY and settings.YOUTUBE_API_KEY.strip()),
        "scheduler": scheduler.get_status(),
    }
