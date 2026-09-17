import asyncio
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.channel import Channel
from app.models.video import Video
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.services.youtube import youtube_service

logger = logging.getLogger("sociator.scheduler")


class SyncScheduler:
    """
    Background asynchronous scheduler for periodic YouTube metrics synchronization.
    Runs periodically within the FastAPI application lifecycle.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self.last_run_at: Optional[datetime] = None
        self.last_run_status: str = "idle"
        self.last_synced_count: int = 0
        self.last_error: Optional[str] = None
        self.next_run_at: Optional[datetime] = None

    def start(self) -> None:
        """Start the periodic background synchronization worker."""
        if not settings.AUTO_SYNC_ENABLED:
            logger.info("Auto-sync is disabled via settings (AUTO_SYNC_ENABLED=False).")
            return

        if self._is_running:
            logger.warning("Auto-sync scheduler is already running.")
            return

        self._is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Auto-sync scheduler started. Runs every {settings.AUTO_SYNC_INTERVAL_HOURS} hours."
        )

    async def stop(self) -> None:
        """Gracefully cancel and await background worker shutdown."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Auto-sync scheduler gracefully stopped.")

    def get_status(self) -> Dict[str, Any]:
        """Return runtime status of the scheduler."""
        return {
            "enabled": settings.AUTO_SYNC_ENABLED,
            "is_running": self._is_running,
            "interval_hours": settings.AUTO_SYNC_INTERVAL_HOURS,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_run_status": self.last_run_status,
            "last_synced_count": self.last_synced_count,
            "last_error": self.last_error,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
        }

    async def _run_loop(self) -> None:
        """Main periodic loop."""
        # Wait a short grace period after server boot before first sync check
        await asyncio.sleep(15)

        while self._is_running:
            try:
                await self.sync_all_now()
            except Exception as e:
                logger.error(f"Scheduler execution error: {e}", exc_info=True)
                self.last_error = str(e)
                self.last_run_status = "error"

            interval_seconds = max(settings.AUTO_SYNC_INTERVAL_HOURS * 3600, 60)
            self.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
            try:
                await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                break

    async def sync_all_now(self) -> Dict[str, Any]:
        """Performs a full sync cycle across all tracked channels."""
        self.last_run_at = datetime.now(timezone.utc)
        self.last_run_status = "running"
        self.last_error = None

        if not settings.YOUTUBE_API_KEY:
            self.last_run_status = "skipped_no_api_key"
            logger.warning("Auto-sync skipped: YOUTUBE_API_KEY is not configured.")
            return {"status": "skipped", "reason": "No API key"}

        db = SessionLocal()
        synced = 0
        failed = 0
        try:
            channels = db.scalars(select(Channel)).all()
            if not channels:
                self.last_run_status = "success_no_channels"
                self.last_synced_count = 0
                return {"status": "success", "synced_channels": 0}

            for channel in channels:
                try:
                    yt_data = await youtube_service.get_channel_info(channel.channel_id)
                    channel.title = yt_data["title"]
                    channel.description = yt_data["description"]
                    channel.custom_url = yt_data["custom_url"]
                    channel.thumbnail_url = yt_data["thumbnail_url"]
                    channel.country = yt_data["country"]
                    channel.view_count = yt_data["view_count"]
                    channel.subscriber_count = yt_data["subscriber_count"]
                    channel.video_count = yt_data["video_count"]

                    # Add analytics snapshot
                    snapshot = AnalyticsSnapshot(
                        channel_id=channel.id,
                        entity_type="channel",
                        views=channel.view_count,
                        subscribers=channel.subscriber_count,
                    )
                    db.add(snapshot)

                    # Update latest 10 videos
                    uploads_id = yt_data.get("uploads_playlist_id")
                    if uploads_id:
                        try:
                            videos = await youtube_service.get_latest_videos(uploads_id, max_results=10)
                            for v in videos:
                                existing_v = db.scalar(select(Video).where(Video.video_id == v["video_id"]))
                                if existing_v:
                                    existing_v.view_count = v["view_count"]
                                    existing_v.like_count = v["like_count"]
                                    existing_v.comment_count = v["comment_count"]
                                else:
                                    db.add(Video(
                                        channel_id=channel.id,
                                        video_id=v["video_id"],
                                        title=v["title"],
                                        description=v["description"],
                                        published_at=v["published_at"],
                                        thumbnail_url=v["thumbnail_url"],
                                        duration=v["duration"],
                                        view_count=v["view_count"],
                                        like_count=v["like_count"],
                                        comment_count=v["comment_count"],
                                    ))
                        except Exception as ve:
                            logger.warning(f"Failed updating videos for {channel.title}: {ve}")

                    synced += 1
                except Exception as ce:
                    failed += 1
                    logger.warning(f"Failed to auto-sync channel {channel.title} ({channel.channel_id}): {ce}")

            db.commit()
            self.last_synced_count = synced
            self.last_run_status = "success" if failed == 0 else f"partial_{synced}_synced_{failed}_failed"
            logger.info(f"Auto-sync completed: {synced} synced, {failed} failed.")
            return {"status": self.last_run_status, "synced_channels": synced, "failed_channels": failed}
        except Exception as e:
            db.rollback()
            self.last_run_status = "error"
            self.last_error = str(e)
            raise
        finally:
            db.close()


scheduler = SyncScheduler()
