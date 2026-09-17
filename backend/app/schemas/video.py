from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class VideoBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    duration: Optional[str] = Field(None, max_length=50)
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0


class VideoCreate(VideoBase):
    video_id: str = Field(..., max_length=50)
    channel_id: int


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None


class VideoResponse(VideoBase):
    id: int
    channel_id: int
    video_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VideoTrackRequest(BaseModel):
    identifier: str = Field(
        ...,
        description="YouTube Video ID or full video URL (e.g. https://youtu.be/dQw4w9WgXcQ)",
    )


class VideoComment(BaseModel):
    comment_id: str
    author_name: str
    author_profile_image: Optional[str] = None
    text: str
    like_count: int = 0
    published_at: Optional[str] = None
