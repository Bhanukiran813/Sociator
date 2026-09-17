from datetime import datetime
from typing import List, Optional
from sqlalchemy import BigInteger, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Channel(Base):
    """
    Represents a tracked YouTube Channel.
    """
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    custom_url: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Core Channel Metrics
    view_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    subscriber_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    videos: Mapped[List["Video"]] = relationship(
        "Video",
        back_populates="channel",
        cascade="all, delete-orphan",
    )
    snapshots: Mapped[List["AnalyticsSnapshot"]] = relationship(
        "AnalyticsSnapshot",
        back_populates="channel",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Channel(id={self.id}, channel_id='{self.channel_id}', title='{self.title}')>"
