from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AnalyticsSnapshot(Base):
    """
    Stores point-in-time performance metric snapshots for historical tracking
    and growth analysis of channels and videos.
    """
    __tablename__ = "analytics_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    channel_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("channels.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    video_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'channel' or 'video'

    # Point-in-time metrics
    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    subscribers: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    likes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    comments: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    # Relationships
    channel: Mapped[Optional["Channel"]] = relationship("Channel", back_populates="snapshots")
    video: Mapped[Optional["Video"]] = relationship("Video", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<AnalyticsSnapshot(id={self.id}, type='{self.entity_type}', recorded_at='{self.recorded_at}')>"
