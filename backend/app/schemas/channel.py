from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ChannelBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    custom_url: Optional[str] = Field(None, max_length=150)
    published_at: Optional[datetime] = None
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    country: Optional[str] = Field(None, max_length=10)
    view_count: int = 0
    subscriber_count: int = 0
    video_count: int = 0


class ChannelCreate(ChannelBase):
    channel_id: str = Field(..., max_length=100)


class ChannelUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    custom_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    country: Optional[str] = None
    view_count: Optional[int] = None
    subscriber_count: Optional[int] = None
    video_count: Optional[int] = None


class ChannelTrackRequest(BaseModel):
    """
    Request body for tracking a channel by YouTube channel ID, custom handle (e.g. @MrBeast), or URL.
    """
    identifier: str = Field(
        ...,
        description="YouTube channel ID (UC...), handle (@username), or channel URL",
        examples=["@MrBeast", "UC_x5XG1OV2P6uZZ5FSM9Ttw"],
    )


class ChannelResponse(ChannelBase):
    id: int
    channel_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChannelSearchResult(BaseModel):
    channel_id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    published_at: Optional[str] = None
