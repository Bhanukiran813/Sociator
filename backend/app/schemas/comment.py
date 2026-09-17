from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    youtube_comment_id: str = Field(..., max_length=100)
    author_name: Optional[str] = Field(None, max_length=255)
    author_profile_image: Optional[str] = Field(None, max_length=500)
    text: str
    like_count: int = 0
    published_at: Optional[datetime] = None


class CommentResponse(CommentBase):
    id: int
    video_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentSyncResponse(BaseModel):
    video_id: int
    youtube_video_id: str
    comments_fetched: int
    comments_created: int
    comments_updated: int


class CommentListResponse(BaseModel):
    items: List[CommentResponse]
    total: int
    skip: int
    limit: int
