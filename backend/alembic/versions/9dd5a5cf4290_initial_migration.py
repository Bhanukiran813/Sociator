"""initial migration

Revision ID: 9dd5a5cf4290
Revises: 
Create Date: 2026-09-16 08:45:13.182622

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9dd5a5cf4290'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create channels table
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('custom_url', sa.String(length=150), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('country', sa.String(length=10), nullable=True),
        sa.Column('view_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('subscriber_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('video_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_channels_id'), 'channels', ['id'], unique=False)
    op.create_index(op.f('ix_channels_channel_id'), 'channels', ['channel_id'], unique=True)

    # 2. Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('duration', sa.String(length=50), nullable=True),
        sa.Column('view_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('comment_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)
    op.create_index(op.f('ix_videos_video_id'), 'videos', ['video_id'], unique=True)
    op.create_index(op.f('ix_videos_channel_id'), 'videos', ['channel_id'], unique=False)

    # 3. Create analytics_snapshots table
    op.create_table(
        'analytics_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('channel_id', sa.Integer(), nullable=True),
        sa.Column('video_id', sa.Integer(), nullable=True),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('views', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('subscribers', sa.BigInteger(), nullable=True),
        sa.Column('likes', sa.BigInteger(), nullable=True),
        sa.Column('comments', sa.BigInteger(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['channel_id'], ['channels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analytics_snapshots_id'), 'analytics_snapshots', ['id'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_channel_id'), 'analytics_snapshots', ['channel_id'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_video_id'), 'analytics_snapshots', ['video_id'], unique=False)
    op.create_index(op.f('ix_analytics_snapshots_recorded_at'), 'analytics_snapshots', ['recorded_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analytics_snapshots_recorded_at'), table_name='analytics_snapshots')
    op.drop_index(op.f('ix_analytics_snapshots_video_id'), table_name='analytics_snapshots')
    op.drop_index(op.f('ix_analytics_snapshots_channel_id'), table_name='analytics_snapshots')
    op.drop_index(op.f('ix_analytics_snapshots_id'), table_name='analytics_snapshots')
    op.drop_table('analytics_snapshots')

    op.drop_index(op.f('ix_videos_channel_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_video_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_table('videos')

    op.drop_index(op.f('ix_channels_channel_id'), table_name='channels')
    op.drop_index(op.f('ix_channels_id'), table_name='channels')
    op.drop_table('channels')
