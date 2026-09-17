from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.db.helpers import find_channel_by_identifier
from app.models.channel import Channel
from app.models.video import Video
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.schemas.channel import ChannelResponse, ChannelTrackRequest, ChannelSearchResult
from app.services.youtube import youtube_service

router = APIRouter()


@router.post("/track", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def track_channel(
    request: ChannelTrackRequest,
    db: Session = Depends(get_db),
):
    """
    Track a new YouTube channel by its handle (e.g., @MrBeast), channel ID (UC...), or URL.
    Fetches real-time channel metadata and statistics from YouTube, saves to database,
    and records an initial analytics snapshot.
    """
    # 1. Fetch channel info from YouTube Data API
    yt_data = await youtube_service.get_channel_info(request.identifier)
    channel_id_str = yt_data["channel_id"]

    # 2. Check if already tracked in DB
    channel = db.scalar(select(Channel).where(Channel.channel_id == channel_id_str))

    if channel:
        # Update existing channel
        channel.title = yt_data["title"]
        channel.description = yt_data["description"]
        channel.custom_url = yt_data["custom_url"]
        channel.thumbnail_url = yt_data["thumbnail_url"]
        channel.country = yt_data["country"]
        channel.view_count = yt_data["view_count"]
        channel.subscriber_count = yt_data["subscriber_count"]
        channel.video_count = yt_data["video_count"]
    else:
        # Create new Channel record
        channel = Channel(
            channel_id=channel_id_str,
            title=yt_data["title"],
            description=yt_data["description"],
            custom_url=yt_data["custom_url"],
            published_at=yt_data["published_at"],
            thumbnail_url=yt_data["thumbnail_url"],
            country=yt_data["country"],
            view_count=yt_data["view_count"],
            subscriber_count=yt_data["subscriber_count"],
            video_count=yt_data["video_count"],
        )
        db.add(channel)
        db.flush()

    # 3. Record snapshot
    snapshot = AnalyticsSnapshot(
        channel_id=channel.id,
        entity_type="channel",
        views=channel.view_count,
        subscribers=channel.subscriber_count,
    )
    db.add(snapshot)

    # 4. If uploads playlist is available, fetch and track latest videos
    uploads_id = yt_data.get("uploads_playlist_id")
    if uploads_id:
        try:
            latest_videos = await youtube_service.get_latest_videos(uploads_id, max_results=10)
            for v_data in latest_videos:
                existing_v = db.scalar(select(Video).where(Video.video_id == v_data["video_id"]))
                if not existing_v:
                    new_v = Video(
                        channel_id=channel.id,
                        video_id=v_data["video_id"],
                        title=v_data["title"],
                        description=v_data["description"],
                        published_at=v_data["published_at"],
                        thumbnail_url=v_data["thumbnail_url"],
                        duration=v_data["duration"],
                        view_count=v_data["view_count"],
                        like_count=v_data["like_count"],
                        comment_count=v_data["comment_count"],
                    )
                    db.add(new_v)
        except Exception:
            # Video fetching failure shouldn't abort channel tracking
            pass

    db.commit()
    db.refresh(channel)
    return channel


@router.get("", response_model=List[ChannelResponse])
def list_channels(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by channel title or handle"),
    db: Session = Depends(get_db),
):
    """
    List all tracked YouTube channels with optional title/handle search.
    """
    query = select(Channel)
    if search:
        query = query.where(
            Channel.title.ilike(f"%{search}%") | Channel.custom_url.ilike(f"%{search}%")
        )
    query = query.order_by(Channel.subscriber_count.desc()).offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/search", response_model=List[ChannelSearchResult])
async def search_channels(
    q: str = Query(..., min_length=1, description="Keywords to search YouTube channels"),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of search results"),
):
    """
    Search YouTube directly for channels matching a keyword query.
    Useful for discovering channels before adding them to tracking.
    """
    return await youtube_service.search_channels(query=q, max_results=limit)


@router.post("/sync-all", response_model=Dict[str, Any])
async def sync_all_channels(
    db: Session = Depends(get_db),
):
    """
    Sync all tracked channels from YouTube in one operation,
    recording fresh snapshots and updating recent video statistics.
    """
    channels = db.scalars(select(Channel)).all()
    results = []

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

            # Record snapshot
            snapshot = AnalyticsSnapshot(
                channel_id=channel.id,
                entity_type="channel",
                views=channel.view_count,
                subscribers=channel.subscriber_count,
            )
            db.add(snapshot)

            # Sync latest videos if available
            uploads_id = yt_data.get("uploads_playlist_id")
            if uploads_id:
                try:
                    latest_videos = await youtube_service.get_latest_videos(uploads_id, max_results=10)
                    for v_data in latest_videos:
                        existing_v = db.scalar(select(Video).where(Video.video_id == v_data["video_id"]))
                        if existing_v:
                            existing_v.view_count = v_data["view_count"]
                            existing_v.like_count = v_data["like_count"]
                            existing_v.comment_count = v_data["comment_count"]
                        else:
                            new_v = Video(
                                channel_id=channel.id,
                                video_id=v_data["video_id"],
                                title=v_data["title"],
                                description=v_data["description"],
                                published_at=v_data["published_at"],
                                thumbnail_url=v_data["thumbnail_url"],
                                duration=v_data["duration"],
                                view_count=v_data["view_count"],
                                like_count=v_data["like_count"],
                                comment_count=v_data["comment_count"],
                            )
                            db.add(new_v)
                except Exception:
                    pass

            results.append({
                "id": channel.id,
                "title": channel.title,
                "status": "success",
                "subscribers": channel.subscriber_count,
                "views": channel.view_count,
            })
        except Exception as e:
            results.append({
                "id": channel.id,
                "title": channel.title,
                "status": "failed",
                "error": str(e),
            })

    db.commit()
    return {
        "total_channels": len(channels),
        "synced_count": len([r for r in results if r["status"] == "success"]),
        "results": results,
    }


@router.get("/{channel_identifier}", response_model=ChannelResponse)
def get_channel(
    channel_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a tracked channel.
    Accepts internal database ID (e.g. '1'), YouTube channel ID ('UC...'), or handle ('@MrBeast').
    """
    channel = find_channel_by_identifier(db, channel_identifier)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked channel '{channel_identifier}' not found.",
        )
    return channel


@router.post("/{channel_identifier}/sync", response_model=ChannelResponse)
async def sync_channel(
    channel_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Sync fresh metrics from YouTube for a tracked channel and save a new analytics snapshot.
    Accepts internal database ID (e.g. '1'), YouTube channel ID ('UC...'), or handle ('@MrBeast').
    """
    channel = find_channel_by_identifier(db, channel_identifier)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked channel '{channel_identifier}' not found.",
        )

    yt_data = await youtube_service.get_channel_info(channel.channel_id)

    channel.title = yt_data["title"]
    channel.description = yt_data["description"]
    channel.custom_url = yt_data["custom_url"]
    channel.thumbnail_url = yt_data["thumbnail_url"]
    channel.country = yt_data["country"]
    channel.view_count = yt_data["view_count"]
    channel.subscriber_count = yt_data["subscriber_count"]
    channel.video_count = yt_data["video_count"]

    # Record snapshot
    snapshot = AnalyticsSnapshot(
        channel_id=channel.id,
        entity_type="channel",
        views=channel.view_count,
        subscribers=channel.subscriber_count,
    )
    db.add(snapshot)

    # Sync latest videos if available
    uploads_id = yt_data.get("uploads_playlist_id")
    if uploads_id:
        try:
            latest_videos = await youtube_service.get_latest_videos(uploads_id, max_results=10)
            for v_data in latest_videos:
                existing_v = db.scalar(select(Video).where(Video.video_id == v_data["video_id"]))
                if existing_v:
                    existing_v.view_count = v_data["view_count"]
                    existing_v.like_count = v_data["like_count"]
                    existing_v.comment_count = v_data["comment_count"]
                else:
                    new_v = Video(
                        channel_id=channel.id,
                        video_id=v_data["video_id"],
                        title=v_data["title"],
                        description=v_data["description"],
                        published_at=v_data["published_at"],
                        thumbnail_url=v_data["thumbnail_url"],
                        duration=v_data["duration"],
                        view_count=v_data["view_count"],
                        like_count=v_data["like_count"],
                        comment_count=v_data["comment_count"],
                    )
                    db.add(new_v)
        except Exception:
            pass

    db.commit()
    db.refresh(channel)
    return channel


@router.delete("/{channel_identifier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Remove a channel from tracking along with its associated videos and snapshots.
    Accepts internal database ID (e.g. '1'), YouTube channel ID ('UC...'), or handle ('@MrBeast').
    """
    channel = find_channel_by_identifier(db, channel_identifier)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked channel '{channel_identifier}' not found.",
        )
    db.delete(channel)
    db.commit()
    return None
