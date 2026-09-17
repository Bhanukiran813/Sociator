from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.db.helpers import find_channel_by_identifier
from app.models.channel import Channel
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.schemas.analytics import (
    ChannelGrowthSummary,
    MetricGrowth,
    SnapshotResponse,
    ChannelLeaderboardItem,
    ChannelComparisonItem,
)

router = APIRouter()


@router.get("/leaderboard", response_model=List[ChannelLeaderboardItem])
def get_leaderboard(
    sort_by: str = Query("subscribers", enum=["subscribers", "views", "videos", "avg_views"]),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get creator leaderboard ranking all tracked channels by subscribers, views, video volume, or avg views per video.
    """
    channels = db.scalars(select(Channel)).all()

    items = []
    for ch in channels:
        avg_v = (ch.view_count // ch.video_count) if ch.video_count > 0 else 0
        items.append({
            "id": ch.id,
            "channel_id": ch.channel_id,
            "title": ch.title,
            "custom_url": ch.custom_url,
            "thumbnail_url": ch.thumbnail_url,
            "subscriber_count": ch.subscriber_count,
            "view_count": ch.view_count,
            "video_count": ch.video_count,
            "avg_views_per_video": avg_v,
        })

    # Sort items
    sort_key_map = {
        "subscribers": lambda x: x["subscriber_count"],
        "views": lambda x: x["view_count"],
        "videos": lambda x: x["video_count"],
        "avg_views": lambda x: x["avg_views_per_video"],
    }
    key_fn = sort_key_map.get(sort_by, sort_key_map["subscribers"])
    items.sort(key=key_fn, reverse=True)

    # Assign ranks
    leaderboard = []
    for idx, item in enumerate(items[:limit], start=1):
        leaderboard.append(ChannelLeaderboardItem(rank=idx, **item))

    return leaderboard


@router.get("/compare", response_model=List[ChannelComparisonItem])
def compare_channels(
    identifiers: str = Query(
        ...,
        description="Comma-separated channel IDs, handles, or database IDs (e.g. '@MrBeast,@veritasium')",
        examples=["@MrBeast,@veritasium"],
    ),
    db: Session = Depends(get_db),
):
    """
    Compare two or more tracked channels side-by-side with metrics, growth stats, and average views.
    """
    id_list = [i.strip() for i in identifiers.split(",") if i.strip()]
    if not id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one channel identifier in the 'identifiers' query parameter.",
        )

    results = []
    for ident in id_list:
        ch = find_channel_by_identifier(db, ident)
        if not ch:
            continue

        # Fetch snapshots
        snapshots = (
            db.scalars(
                select(AnalyticsSnapshot)
                .where(
                    AnalyticsSnapshot.channel_id == ch.id,
                    AnalyticsSnapshot.entity_type == "channel",
                )
                .order_by(AnalyticsSnapshot.recorded_at.asc())
            )
            .all()
        )

        # Growth calculation
        current_views = ch.view_count
        prev_views = snapshots[0].views if snapshots else current_views
        v_diff = current_views - prev_views
        v_pct = (v_diff / prev_views * 100.0) if prev_views > 0 else 0.0

        current_subs = ch.subscriber_count
        prev_subs = snapshots[0].subscribers or 0 if snapshots else current_subs
        s_diff = current_subs - prev_subs
        s_pct = (s_diff / prev_subs * 100.0) if prev_subs > 0 else 0.0

        avg_views = (ch.view_count // ch.video_count) if ch.video_count > 0 else 0

        results.append(
            ChannelComparisonItem(
                id=ch.id,
                channel_id=ch.channel_id,
                title=ch.title,
                custom_url=ch.custom_url,
                thumbnail_url=ch.thumbnail_url,
                subscriber_count=ch.subscriber_count,
                view_count=ch.view_count,
                video_count=ch.video_count,
                avg_views_per_video=avg_views,
                views_growth=MetricGrowth(
                    current=current_views,
                    previous=prev_views if len(snapshots) > 1 else None,
                    change=v_diff,
                    growth_rate_pct=round(v_pct, 2),
                ),
                subs_growth=MetricGrowth(
                    current=current_subs,
                    previous=prev_subs if len(snapshots) > 1 else None,
                    change=s_diff,
                    growth_rate_pct=round(s_pct, 2),
                ),
            )
        )

    return results


@router.get("/channel/{channel_identifier}", response_model=ChannelGrowthSummary)
def get_channel_analytics(
    channel_identifier: str,
    db: Session = Depends(get_db),
):
    """
    Get growth summary and historical analytics performance for a tracked channel.
    Accepts database ID (e.g. '1'), YouTube channel ID ('UC...'), or handle ('@MrBeast').
    """
    channel = find_channel_by_identifier(db, channel_identifier)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked channel '{channel_identifier}' not found.",
        )

    # Fetch snapshots ordered chronologically
    snapshots = (
        db.scalars(
            select(AnalyticsSnapshot)
            .where(
                AnalyticsSnapshot.channel_id == channel.id,
                AnalyticsSnapshot.entity_type == "channel",
            )
            .order_by(AnalyticsSnapshot.recorded_at.asc())
        )
        .all()
    )

    # Calculate view growth
    current_views = channel.view_count
    prev_views = snapshots[0].views if snapshots else current_views
    view_diff = current_views - prev_views
    view_pct = (view_diff / prev_views * 100.0) if prev_views > 0 else 0.0

    views_growth = MetricGrowth(
        current=current_views,
        previous=prev_views if len(snapshots) > 1 else None,
        change=view_diff,
        growth_rate_pct=round(view_pct, 2),
    )

    # Calculate subscriber growth
    current_subs = channel.subscriber_count
    prev_subs = snapshots[0].subscribers or 0 if snapshots else current_subs
    sub_diff = current_subs - prev_subs
    sub_pct = (sub_diff / prev_subs * 100.0) if prev_subs > 0 else 0.0

    subs_growth = MetricGrowth(
        current=current_subs,
        previous=prev_subs if len(snapshots) > 1 else None,
        change=sub_diff,
        growth_rate_pct=round(sub_pct, 2),
    )

    return ChannelGrowthSummary(
        channel_id=channel.channel_id,
        title=channel.title,
        views=views_growth,
        subscribers=subs_growth,
        videos_count=channel.video_count,
        history=[SnapshotResponse.model_validate(s) for s in snapshots],
    )


@router.get("/channel/{channel_identifier}/snapshots", response_model=List[SnapshotResponse])
def get_channel_snapshots(
    channel_identifier: str,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Retrieve raw recorded snapshots for a channel.
    Accepts database ID (e.g. '1'), YouTube channel ID ('UC...'), or handle ('@MrBeast').
    """
    channel = find_channel_by_identifier(db, channel_identifier)
    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tracked channel '{channel_identifier}' not found.",
        )

    snapshots = (
        db.scalars(
            select(AnalyticsSnapshot)
            .where(
                AnalyticsSnapshot.channel_id == channel.id,
                AnalyticsSnapshot.entity_type == "channel",
            )
            .order_by(AnalyticsSnapshot.recorded_at.desc())
            .limit(limit)
        )
        .all()
    )
    return snapshots
