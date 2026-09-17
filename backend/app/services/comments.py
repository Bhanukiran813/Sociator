from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.video import Video
from app.services.youtube import youtube_service
from app.schemas.comment import CommentSyncResponse


class CommentService:
    """
    Handles database persistence, synchronization, and retrieval of YouTube comments.
    Separates external YouTube API fetching from PostgreSQL database persistence.
    """

    async def sync_video_comments(
        self,
        db: Session,
        video: Video,
        max_results: int = 100,
    ) -> CommentSyncResponse:
        """
        Fetches comments from YouTube via YouTubeService and synchronizes them into PostgreSQL.
        Inserts new comments and updates metrics/text on existing ones without creating duplicates.
        """
        # 1. Fetch comments from YouTube
        raw_comments = await youtube_service.get_video_comments(
            raw_video=video.video_id,
            max_results=max_results,
        )

        comments_fetched = len(raw_comments)
        comments_created = 0
        comments_updated = 0

        if not raw_comments:
            return CommentSyncResponse(
                video_id=video.id,
                youtube_video_id=video.video_id,
                comments_fetched=0,
                comments_created=0,
                comments_updated=0,
            )

        # 2. Extract comment IDs to check existing records in bulk
        yt_comment_ids = [c["comment_id"] for c in raw_comments if c.get("comment_id")]
        existing_comments_stmt = select(Comment).where(
            Comment.youtube_comment_id.in_(yt_comment_ids)
        )
        existing_comments_map = {
            c.youtube_comment_id: c for c in db.scalars(existing_comments_stmt).all()
        }

        # 3. Create or update comments safely
        try:
            for c_data in raw_comments:
                cid = c_data.get("comment_id")
                if not cid:
                    continue

                pub_at_raw = c_data.get("published_at")
                pub_at_dt: Optional[datetime] = None
                if pub_at_raw:
                    try:
                        pub_at_dt = datetime.fromisoformat(pub_at_raw.replace("Z", "+00:00"))
                    except Exception:
                        pub_at_dt = None

                text = c_data.get("text", "")
                like_count = int(c_data.get("like_count", 0))
                author_name = c_data.get("author_name")
                author_profile_image = c_data.get("author_profile_image")

                if cid in existing_comments_map:
                    # Update existing comment
                    comment = existing_comments_map[cid]
                    updated = False
                    if comment.text != text:
                        comment.text = text
                        updated = True
                    if comment.like_count != like_count:
                        comment.like_count = like_count
                        updated = True
                    if author_name and comment.author_name != author_name:
                        comment.author_name = author_name
                        updated = True
                    if author_profile_image and comment.author_profile_image != author_profile_image:
                        comment.author_profile_image = author_profile_image
                        updated = True

                    if updated:
                        comments_updated += 1
                else:
                    # Create new comment record
                    new_comment = Comment(
                        video_id=video.id,
                        youtube_comment_id=cid,
                        author_name=author_name,
                        author_profile_image=author_profile_image,
                        text=text,
                        like_count=like_count,
                        published_at=pub_at_dt,
                    )
                    db.add(new_comment)
                    # Add to map to prevent intra-batch duplicate additions
                    existing_comments_map[cid] = new_comment
                    comments_created += 1

            db.commit()
        except Exception:
            db.rollback()
            raise

        return CommentSyncResponse(
            video_id=video.id,
            youtube_video_id=video.video_id,
            comments_fetched=comments_fetched,
            comments_created=comments_created,
            comments_updated=comments_updated,
        )

    def get_comments_for_video(
        self,
        db: Session,
        video_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[Comment], int]:
        """
        Retrieves stored comments for a video ordered by published date descending,
        with pagination and total count.
        """
        count_query = select(func.count(Comment.id)).where(Comment.video_id == video_id)
        total = db.scalar(count_query) or 0

        items_query = (
            select(Comment)
            .where(Comment.video_id == video_id)
            .order_by(Comment.published_at.desc().nulls_last(), Comment.id.desc())
            .offset(skip)
            .limit(limit)
        )
        items = list(db.scalars(items_query).all())

        return items, total


comment_service = CommentService()
