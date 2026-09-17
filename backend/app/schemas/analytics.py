from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class SnapshotResponse(BaseModel):
    id: int
    channel_id: Optional[int] = None
    video_id: Optional[int] = None
    entity_type: str
    views: int
    subscribers: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    recorded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MetricGrowth(BaseModel):
    current: int
    previous: Optional[int] = None
    change: int = 0
    growth_rate_pct: float = 0.0


class ChannelGrowthSummary(BaseModel):
    channel_id: str
    title: str
    views: MetricGrowth
    subscribers: MetricGrowth
    videos_count: int
    history: List[SnapshotResponse]


class ChannelLeaderboardItem(BaseModel):
    rank: int
    id: int
    channel_id: str
    title: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int
    view_count: int
    video_count: int
    avg_views_per_video: int


class ChannelComparisonItem(BaseModel):
    id: int
    channel_id: str
    title: str
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subscriber_count: int
    view_count: int
    video_count: int
    avg_views_per_video: int
    views_growth: MetricGrowth
    subs_growth: MetricGrowth
