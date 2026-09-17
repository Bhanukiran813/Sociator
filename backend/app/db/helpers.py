from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.channel import Channel
from app.models.video import Video


def find_channel_by_identifier(db: Session, identifier: str) -> Optional[Channel]:
    """
    Finds a Channel by:
    1. Internal database integer ID (e.g. '1')
    2. YouTube alphanumeric channel ID (e.g. 'UCHnyfMqiRRG1u-2MsSQLbXA')
    3. Channel handle (e.g. '@veritasium' or 'veritasium')
    """
    clean_id = identifier.strip()

    # 1. Check if integer database ID
    if clean_id.isdigit():
        ch = db.get(Channel, int(clean_id))
        if ch:
            return ch

    # 2. Check by official YouTube channel_id
    ch = db.scalar(select(Channel).where(Channel.channel_id == clean_id))
    if ch:
        return ch

    # 3. Check by handle (with or without '@')
    handle = clean_id if clean_id.startswith("@") else f"@{clean_id}"
    ch = db.scalar(select(Channel).where(Channel.custom_url.ilike(handle)))
    if ch:
        return ch

    # 4. Fallback search by title or partial handle
    return db.scalar(select(Channel).where(Channel.custom_url.ilike(f"%{clean_id}%")))


def find_video_by_identifier(db: Session, identifier: str) -> Optional[Video]:
    """
    Finds a Video by:
    1. Internal database integer ID (e.g. '12')
    2. YouTube 11-character video ID (e.g. 'dQw4w9WgXcQ')
    """
    clean_id = identifier.strip()

    # 1. Check if integer database ID
    if clean_id.isdigit():
        v = db.get(Video, int(clean_id))
        if v:
            return v

    # 2. Check by YouTube video_id
    return db.scalar(select(Video).where(Video.video_id == clean_id))
