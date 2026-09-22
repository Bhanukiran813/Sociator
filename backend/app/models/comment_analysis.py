from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.comment import Comment


class CommentAnalysis(Base):
    """
    Stores AI-powered analysis metrics for a YouTube comment.
    Separated from the core Comment entity to allow re-analysis
    and independent lifecycle management.
    """
    __tablename__ = "comment_analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    topic: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_actionable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    analyzed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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
    comment: Mapped["Comment"] = relationship("Comment", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<CommentAnalysis(id={self.id}, comment_id={self.comment_id}, sentiment='{self.sentiment}', model='{self.model}')>"
