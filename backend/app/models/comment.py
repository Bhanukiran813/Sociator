from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Comment(Base):
    """
    Represents a stored YouTube comment associated with a tracked Video.
    Lays the foundation for Comment Intelligence, topic modeling, and sentiment analysis.
    """
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("videos.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    youtube_comment_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    author_profile_image: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    like_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=True,
    )

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
    video: Mapped["Video"] = relationship("Video", back_populates="comments")

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, youtube_comment_id='{self.youtube_comment_id}', video_id={self.video_id})>"
