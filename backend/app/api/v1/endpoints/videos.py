from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.db.helpers import find_video_by_identifier, find_channel_by_identifier
from app.models.channel import Channel
from app.models.video import Video
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.schemas.video import VideoResponse, VideoTrackRequest, VideoComment
from app.services.youtube import youtube_service

router = APIRouter()


@router.post("/track", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
async def track_video(
    request: VideoTrackRequest,
    db: Session = Depends(get_db),
):
    """
    Track an individual YouTube video by video ID, watch URL, or short URL.
    Fetches real-time video details and statistics, links to or creates the parent channel,
    and logs an analytics snapshot.
    """
    # 1. Fetch video metadata from YouTube
    v_info = await youtube_service.get_video_info(request.identifier)
    yt_vid_id = v_info["video_id"]
    yt_channel_id = v_info["channel_id"]

    # 2. Check or create parent channel
    channel = db.scalar(select(Channel).where(Channel.channel_id == yt_channel_id))
    if not channel:
        try:
            ch_data = await youtube_service.get_channel_info(yt_channel_id)
            channel = Channel(
                channel_id=ch_data["channel_id"],
                title=ch_data["title"],
                description=ch_data["description"],
                custom_url=ch_data["custom_url"],
                published_at=ch_data["published_at"],
                thumbnail_url=ch_data["thumbnail_url"],
                country=ch_data["country"],
                view_count=ch_data["view_count"],
                subscriber_count=ch_data["subscriber_count"],
                video_count=ch_data["video_count"],
            )
            db.add(channel)
            db.flush()
        except Exception:
            channel = Channel(
                channel_id=yt_channel_id,
                title=v_info.get("channel_title", "Unknown Channel"),
            )
            db.add(channel)
            db.flush()

    # 3. Check or create Video record
    video = db.scalar(select(Video).where(Video.video_id == yt_vid_id))
    if video:
        video.title = v_info["title"]
        video.description = v_info["description"]
        video.thumbnail_url = v_info["thumbnail_url"]
        video.duration = v_info["duration"]
        video.view_count = v_info["view_count"]
        video.like_count = v_info["like_count"]
        video.comment_count = v_info["comment_count"]
    else:
        video = Video(
            channel_id=channel.id,
            video_id=yt_vid_id,
            title=v_info["title"],
            description=v_info["description"],
            published_at=v_info["published_at"],
            thumbnail_url=v_info["thumbnail_url"],
            duration=v_info["duration"],
            view_count=v_info["view_count"],
            like_count=v_info["like_count"],
            comment_count=v_info["comment_count"],
        )
        db.add(video)
        db.flush()

    # 4. Record snapshot
    snapshot = AnalyticsSnapshot(
        video_id=video.id,
        channel_id=channel.id,
        entity_type="video",
        views=video.view_count,
        likes=video.like_count,
        comments=video.comment_count,
    )
    db.add(snapshot)

    db.commit()
    db.refresh(video)
    return video


@router.get("", response_model=List[VideoResponse])
def list_videos(
    channel: Optional[str] = Query(None, description="Filter by channel DB ID, handle (e.g. @MrBeast), or YouTube ID"),
    sort_by: str = Query("published_at", enum=["published_at", "views", "likes", "comments"]),
    order: str = Query("desc", enum=["asc", "desc"]),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    List tracked YouTube videos with optional filtering by channel and sorting by views, likes, or date.
    """
    query = select(Video)
    if channel:
        ch = find_channel_by_identifier(db, channel)
        if ch:
            query = query.where(Video.channel_id == ch.id)
        elif channel.isdigit():
            query = query.where(Video.channel_id == int(channel))
        else:
            return []

    # Sort ordering
    sort_column_map = {
        "published_at": Video.published_at,
        "views": Video.view_count,
        "likes": Video.like_count,
        "comments": Video.comment_count,
    }
    col = sort_column_map.get(sort_by, Video.published_at)
    query = query.order_by(desc(col) if order == "desc" else col)

    query = query.offset(skip).limit(limit)
    return db.scalars(query).all()


@router.get("/{video_identifier}", response_model=VideoResponse)
def get_video(
    video_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a specific video.
    Accepts database ID (e.g. '1') or YouTube 11-char video ID (e.g. 'dQw4w9WgXcQ').
    """
    video = find_video_by_identifier(db, video_identifier)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked video '{video_identifier}' not found.",
        )
    return video


@router.post("/{video_identifier}/sync", response_model=VideoResponse)
async def sync_video(
    video_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Sync fresh statistics for a tracked video from YouTube and record a new snapshot.
    Accepts database ID (e.g. '1') or YouTube 11-char video ID.
    """
    video = find_video_by_identifier(db, video_identifier)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked video '{video_identifier}' not found.",
        )

    v_info = await youtube_service.get_video_info(video.video_id)

    video.title = v_info["title"]
    video.description = v_info["description"]
    video.thumbnail_url = v_info["thumbnail_url"]
    video.duration = v_info["duration"]
    video.view_count = v_info["view_count"]
    video.like_count = v_info["like_count"]
    video.comment_count = v_info["comment_count"]

    # Record snapshot
    snapshot = AnalyticsSnapshot(
        video_id=video.id,
        channel_id=video.channel_id,
        entity_type="video",
        views=video.view_count,
        likes=video.like_count,
        comments=video.comment_count,
    )
    db.add(snapshot)

    db.commit()
    db.refresh(video)
    return video


@router.get("/{video_identifier}/comments", response_model=List[VideoComment])
async def get_video_comments(
    video_identifier: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Fetch top comments for a tracked video directly from YouTube.
    Accepts database ID (e.g. '1') or YouTube 11-char video ID.
    """
    video = find_video_by_identifier(db, video_identifier)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked video '{video_identifier}' not found.",
        )

    return await youtube_service.get_video_comments(video.video_id, max_results=limit)


@router.delete("/{video_identifier}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Remove a tracked video and its associated analytics snapshots.
    Accepts database ID (e.g. '1') or YouTube 11-char video ID.
    """
    video = find_video_by_identifier(db, video_identifier)
    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked video '{video_identifier}' not found.",
        )
    db.delete(video)
    db.commit()
    return None
